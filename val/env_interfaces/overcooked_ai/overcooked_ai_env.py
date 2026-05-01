from typing import List
from typing import Tuple
import copy
import time
from random import choice

from pprint import pprint
import pygame
import numpy as np

from overcooked_ai_py.planning.planners import MotionPlanner
from overcooked_ai_py.mdp.layout_generator import LayoutGenerator
from overcooked_ai_py.mdp.actions import Action
from overcooked_ai_py.mdp.overcooked_env import DEFAULT_ENV_PARAMS
from overcooked_ai_py.mdp.overcooked_env import OvercookedEnv
from overcooked_ai_py.mdp.overcooked_mdp import OvercookedGridworld
from overcooked_ai_py.visualization.state_visualizer import StateVisualizer

from py_search.base import Problem
from py_search.base import Node
from py_search.informed import best_first_search

from val.env_interfaces.abstract_interface import AbstractEnvInterface

from pyhtn.htn import Task, Method, Operator, TaskEx, MethodEx, OperatorEx
from pyhtn.conditions.fact import Fact
from pyhtn.conditions.conditions import NOT
from pyhtn.domain.variable import V


OVERCOOKED_ACT_COMMAND = getattr(Action, "INTER" + "ACT")


def _get_counter_locations(mdp):
    return [
        (x, y)
        for y, row in enumerate(mdp.terrain_mtx)
        for x, terrain in enumerate(row)
        if terrain == "X"
    ]


def _get_occupied_counter_locations(mdp, state):
    counter_objects = mdp.get_counter_objects_dict(state)
    return {
        (x, y)
        for object_locations in counter_objects.values()
        for x, y in object_locations
    }


def _get_empty_counter_locations(mdp, state):
    occupied_counters = _get_occupied_counter_locations(mdp, state)
    return [
        pos
        for pos in _get_counter_locations(mdp)
        if pos not in occupied_counters
    ]


class OvercookedRouteProblem(Problem):

    def successors(self, node):
        """
        Computes successors and computes the value of the node as cost. 
        This will do something like breadth first.
        """
        player_idx, pos, orr = node.state
        actions = [(1,0), (-1, 0), (0, -1), (0, 1)]
        for action in actions:
            new_pos = ((pos[0] + action[0]), pos[1] + action[1])
            player_positions = [p.position for i, p in enumerate(node.extra.state.players) if i != player_idx]
            if node.extra.mdp.terrain_mtx[new_pos[1]][new_pos[0]] == " " and new_pos not in player_positions:
                new_state = (player_idx, new_pos, action)
            else:
                new_state = (player_idx, pos, action)
            path_cost = node.cost() + 1
            yield Node(new_state, node, action, path_cost, extra=node.extra)

    def goal_test(self, state_node, goal_node=None):
        if goal_node is None:
            goal = self.goal
        else:
            goal = goal_node.state

        player_idx, pos, orr = state_node.state
        facing = (pos[0] + orr[0], pos[1] + orr[1])
        target = state_node.extra.mdp.terrain_mtx[facing[1]][facing[0]]

        if goal == "onion":
            return target == 'O'
        if goal == "dish":
            return target == 'D'
        if goal == "tomato":
            return target == 'T'
        if goal == "serving pad":
            return target == 'S'
        if goal == "pot":
            return target == 'P'

        if goal in ["counter", "empty counter", "empty_counter"]:
            return target == "X" and facing in _get_empty_counter_locations(
                state_node.extra.mdp,
                state_node.extra.state
            )

        counter_objects = state_node.extra.mdp.get_counter_objects_dict(state_node.extra.state)
        if goal in counter_objects:
            for ox, oy in counter_objects[goal]:
                if (ox, oy) == facing:
                    return True
    
        return False

class OvercookedAIEnv(AbstractEnvInterface):

    def __init__(self, player_id=0, horizon=5000, layout="asymmetric_advantages", render=True, action_delay_ms=0,
                 show_all_players=False):
        """
        Full list of layouts here:
        https://github.com/HumanCompatibleAI/overcooked_ai/tree/cb2e50cae95accbe4618879d88e565c87c54b1c3/src/overcooked_ai_py/data/layouts
        """
        self.layout = layout
        self.horizon = horizon
        self.player_id = player_id
        self.action_delay_ms = action_delay_ms
        self.show_all_players = show_all_players
        self.reset()

        if self.player_id >= len(self.base_env.state.players):
            raise ValueError(f"Player id must be less than {len(self.base_env.state.players)}")

        self.render = render

        if self.render:
            self.visualizer = StateVisualizer()
            pygame.init()
            self.screen = pygame.display.set_mode((800,600), pygame.RESIZABLE)
            self.clock = pygame.time.Clock()
            self.render_state()

    def reset(self):
        self.mdp = OvercookedGridworld.from_layout_name(self.layout)
        self.base_env = OvercookedEnv.from_mdp(self.mdp, horizon=self.horizon)
        self.motion_planner = MotionPlanner(self.mdp)

    def _get_render_state(self):
        if self.show_all_players:
            return self.base_env.state

        render_state = self.base_env.state.deepcopy()
        render_state.players = (render_state.players[self.player_id],)
        return render_state

    def render_state(self):
        render_state = self._get_render_state()
        player_colors = self.visualizer.player_colors
        if not self.show_all_players:
            self.visualizer.player_colors = [player_colors[self.player_id]]

        try:
            surface = self.visualizer.render_state(state=render_state,
                                                   grid=self.base_env.mdp.terrain_mtx,
                                                   hud_data=StateVisualizer.default_hud_data(
                                                       self.base_env.state))
        finally:
            self.visualizer.player_colors = player_colors

        rendered_width, rendered_height = surface.get_size()
        if (rendered_width, rendered_height) != self.screen.get_size():
            self.screen = pygame.display.set_mode((rendered_width, rendered_height), pygame.RESIZABLE)

        self.screen.blit(surface, (0, 0))
        pygame.display.flip()
        self.clock.tick(10)

    def _pause_after_action(self):
        if self.action_delay_ms > 0:
            time.sleep(self.action_delay_ms / 1000.0)

    def get_objects(self) -> List[str]:
        objects = []
        for i, p in enumerate(self.base_env.state.players):
            objects.append(f"player{i}")

        for ele in self.get_state():
            if 'object' in ele:
                objects.append(ele['object'])

        return objects

    def get_actions(self) -> List[Tuple[str, List[str]]]:
        domain= {}
        descriptions = {}
        
        domain["cook"] = [
            Method(
                name='cook',
                args=(V('object'),),
                preconditions=[],
                subtasks=[
                    Task('get', V('object')),
                    Task('boil',V('object')),
                    Task('plate'),
                    Task('deliver')
                ]
            ),
        ]
        descriptions["cook"] = "Cook soup by sequentially getting, boiling, plating, and delivering the soup."

        domain["get"] = [
            Method(
                name='get',
                args=(V('object'),),
                preconditions=[],
                subtasks=[
                    Task('go to', V('object')),
                    Task('act'),
                ]
            )
        ]
        descriptions["get"] = "Get an object by acting with and moving to the object's location."

        domain["drop"] = [
            Method(
                name='drop',
                preconditions=[
                    NOT(Fact(player_holding='nothing')),
                    Fact(object='counter', status='empty')
                ],
                subtasks=[
                    Task('go to', 'counter'),
                    Task('act'),
                ]
            )
        ]
        descriptions["drop"] = "Drop the held object on an empty counter by moving to the counter and acting."

        # ENHANCED BOIL METHODS WITH POT SELECTION AND PLAYER HOLDING LOGIC
        domain["boil"] = [
            #Method 1: Already holding object, use empty pot1
            Method(
                name='boil',
                args=(V('object'),),
                preconditions=[
                    Fact(player_holding=V('object')),  # Already have the object (PRIORITY)
                    Fact(id='pot1', object='pot1', status='empty')
                ],
                subtasks=[
                    Task('go to', 'pot1'),
                    Task('act')
                ]
            ),
            # #Method 2: Already holding object, use empty pot2
            # Method(
            #     name='boil',
            #     args=(V('object'),),
            #     preconditions=[
            #         Fact(player_holding=V('object')),  # Already have the object (PRIORITY)
            #         Fact(id='pot2', object='pot2', status='empty')
            #     ],
            #     subtasks=[
            #         Task('go to', 'pot2'),
            #         Task('act')
            #     ]
            # ),
            # Method 3: Already holding object, add to pot1 with 1 item (completes recipe)
            Method(
                name='boil',
                args=(V('object'),),
                preconditions=[
                    Fact(player_holding=V('object')),  # Already have the object (PRIORITY)
                    Fact(id='pot1', object='pot1', status='empty')
                ],
                subtasks=[
                    Task('go to', 'pot1'),
                    Task('act'),
                    Task('act'),
                    Task('wait 20min')
                ]
            ),

            # # Method 4: Already holding object, add to pot2 with 1 item (completes recipe)
            # Method(
            #     name='boil',
            #     args=(V('object'),),
            #     preconditions=[
            #         Fact(player_holding=V('object')),  # Already have the object (PRIORITY)
            #         Fact(id='pot2', object='pot2', status='1_items')
            #     ],
            #     subtasks=[
            #         Task('go to', 'pot2'),
            #         Task('act')
            #     ]
            # ),
            # # Method 5: Don't have object, get it first, then use empty pot1
            # Method(
            #     name='boil',
            #     args=(V('object'),),
            #     preconditions=[
            #         NOT(Fact(player_holding=V('object'))),  # Don't have the object yet
            #         Fact(id='pot1', object='pot1', status='empty')
            #     ],
            #     subtasks=[
            #         Task('get', V('object')),
            #         Task('go to', 'pot1'),
            #         Task('act')
            #     ]
            # ),
            # # Method 6: Don't have object, get it first, then use empty pot2
            # Method(
            #     name='boil',
            #     args=(V('object'),),
            #     preconditions=[
            #         NOT(Fact(player_holding=V('object'))),  # Don't have the object yet
            #         Fact(id='pot2', object='pot2', status='empty')
            #     ],
            #     subtasks=[
            #         Task('get', V('object')),
            #         Task('go to', 'pot2'),
            #         Task('act')
            #     ]
            # ),
            # Method 7: Don't have object, get it, add to pot1 with 1 item (completes recipe)
            Method(
                name='boil',
                args=(V('object'),),
                preconditions=[
                    NOT(Fact(player_holding=V('object'))),  # Don't have the object yet
                    Fact(id='pot1', object='pot1', status='1_items')
                ],
                subtasks=[
                    Task('get', V('object')),
                    Task('go to', 'pot1'),
                    Task('act')
                ]
            ),
            # Method 8: Don't have object, get it, add to pot2 with 1 item (completes recipe)
            Method(
                name='boil',
                args=(V('object'),),
                preconditions=[
                    NOT(Fact(player_holding=V('object'))),  # Don't have the object yet
                    Fact(id='pot2', object='pot2', status='1_items')
                ],
                subtasks=[
                    Task('get', V('object')),
                    Task('go to', 'pot2'),
                    Task('act')
                ]
            ),
            # Method 9: Fallback - just act (for when already at pot)
            Method(
                name='boil',
                args=(V('object'),),
                preconditions=[],
                subtasks=[
                    Task('act')
                ]
            )
        ]
        descriptions["boil"] = "Boil the ingredient by moving to a pot and acting with it. Automatically selects pot1 or pot2 based on availability and current state."

        # ENHANCED PLATE METHODS WITH POT SELECTION
        domain["plate"] = [
            # # Method 1: Already have dish, plate from ready pot1
            # Method(
            #     name='plate',
            #     preconditions=[
            #         Fact(player_holding='dish'),
            #         Fact(id='pot1', object='pot1', status='empty')
            #     ],
            #     subtasks=[
            #         Task('go to', 'pot1'),
            #         Task('act')
            #     ]
            # ),
            # # Method 2: Already have dish, plate from ready pot2
            # Method(
            #     name='plate',
            #     preconditions=[
            #         Fact(player_holding='dish'),
            #         Fact(id='pot2', object='pot2', status='empty')
            #     ],
            #     subtasks=[
            #         Task('go to', 'pot2'),
            #         Task('act')
            #     ]
            # ),
            # # Method 3: Already have dish, plate from cooking pot1 (if ready soon)
            # Method(
            #     name='plate',
            #     preconditions=[
            #         Fact(player_holding='dish'),
            #         Fact(id='pot1', object='pot1', status='cooking')
            #     ],
            #     subtasks=[
            #         Task('go to', 'pot1'),
            #         Task('act')
            #     ]
            # ),
            # # Method 4: Already have dish, plate from cooking pot2 (if ready soon)
            # Method(
            #     name='plate',
            #     preconditions=[
            #         Fact(player_holding='dish'),
            #         Fact(id='pot2', object='pot2', status='cooking')
            #     ],
            #     subtasks=[
            #         Task('go to', 'pot2'),
            #         Task('act')
            #     ]
            # ),
            # Method 5: Don't have dish, get it first, then plate from ready pot1
            Method(
                name='plate',
                preconditions=[
                    NOT(Fact(player_holding='dish')),
                ],
                subtasks=[
                    Task('get', 'dish'),
                    Task('go to', 'pot2'),
                    Task('act')
                ]
            ),
            # Method 6: Don't have dish, get it first, then plate from ready pot2
            # Method(
            #     name='plate',
            #     preconditions=[
            #         NOT(Fact(player_holding='dish')),
            #         Fact(id='pot1', object='pot1', status='ready')
            #     ],
            #     subtasks=[
            #         Task('get', 'dish'),
            #         Task('go to', 'pot1'),
            #         Task('act')
            #     ]
            # ),
            # # Method 7: Fallback - get dish and go to any pot
            # Method(
            #     name='plate',
            #     preconditions=[],
            #     subtasks=[
            #         Task('get', 'dish'),
            #         Task('go to', 'pot'),
            #         Task('act')
            #     ]
            # ),
        ]
        descriptions["plate"] = "Plate the soup by going to a ready pot with a dish. Automatically selects pot1 or pot2 based on which pot has ready soup."
        
        # domain["deliver"] = [
        #     Method(
        #         name='deliver',
        #         preconditions=(),
        #         subtasks=[
        #             Task('go to', 'serving pad'),
        #             Task('act')
        #         ]
        #     ),
        # ]
        # descriptions["deliver"] = "Go to the serving pad and act with it to deliver the soup."
        
        ####### operators #######
        domain["go to"] = [
            Operator(
                name='go to', 
                args=(V('location'),),
                effects=[]
            ),
        ]
        descriptions["go to"] = "Goes to and faces the target object, where object is something like pot, pot1, pot2, onion etc."
        
        domain["act"] = [
            Operator(
                name='act',
                args=(),
                preconditions=[],
                effects=[]
            ),
        ]
        descriptions["act"] = "Act with the object, e.g., this should be called if you are trying to act with the pot, plate, tomato, onion, etc."
            
        domain["wait 20min"] = [
            Operator(
                name='wait 20min',
                args=(),
                preconditions=(),
                effects=[]
            ),
        ]
        descriptions["wait 20min"] = "Waits for 20 time steps."
   
        return domain, descriptions
    
    ######################This is for baseline model which only has actions like go to, act, wait 20min
    def get_primary_actions(self) -> List[Tuple[str, List[str]]]:
        domain= {}
        descriptions = {}
        ####### operators #######
        domain["go to"] = [
            Operator(
                name='go to', 
                args=(V('location'),),
                # preconditions=[Fact(type='fact', object=V('location'))],
                effects=[]
            ),
        ]
        descriptions["go to"] = "Goes to and faces the target object, where object is something like pot, pot1, pot2, onion etc."
        
        domain["act"] = [
            Operator(
                name='act',
                args=(),
                preconditions=[],
                effects=[]
            ),
        ]
        descriptions["act"] = "Act with the object, e.g., this should be called if you are trying to act with the pot, plate, tomato, onion, etc."
        domain["wait 20min"] = [
            Operator(
                name='wait 20min',
                args=(),
                preconditions=(),
                effects=[]
            ),
        ]
        descriptions["wait 20min"] = "Waits for 20 time steps."
        domain["left"] = [
            Operator(
                name=('left',),
                preconditions=(),
                effects=[]
            ),
        ]
        descriptions["left"] = "Moves one unit left."

        domain["right"] = [
            Operator(
                name=('right',),
                preconditions=(),
                effects=[]
            ),
        ]
        descriptions["right"] = "Moves one unit right."

        domain["up"] = [
            Operator(
                name=('up',),
                preconditions=(),
                effects=[]
            ),
        ]
        descriptions["up"] = "Moves one unit up."

        domain["down"] = [
            Operator(
                name=('down',),
                preconditions=(),
                effects=[]
            ),
        ]
        descriptions["down"] = "Moves one unit down."
        return domain, descriptions

    def get_player_pos_and_or(self):
        return (self.base_env.state.players[self.player_id].position,
                self.base_env.state.players[self.player_id].orientation)

    def get_state(self) -> dict:
        state = []

        # Players
        for i, player in enumerate(self.base_env.state.players):
            orientation = None
            if player.orientation[0] == -1:
                orientation = "left"
            elif player.orientation[0] == 1:
                orientation = "right"
            elif player.orientation[1] == -1:
                orientation = "down"
            elif player.orientation[1] == 1:
                orientation = "up"

            state.append({
                'id': f'player_{i}',
                'object': 'player',
                'player_index': i,
                'x': player.position[0],
                'y': player.position[1],
                'orientation': orientation,
                'is_me': str(i == self.player_id),
                'holding': player.held_object
            })
            
            # Add player holding status for HTN preconditions
            # CRITICAL: This must match the Fact(player_holding=...) format in HTN methods
            if i == self.player_id:
                if player.held_object is None:
                    state.append({'id': f'player_{i}_holding', 'player_holding': 'nothing'})
                else:
                    state.append({'id': f'player_{i}_holding', 'player_holding': player.held_object.name})

        # Static environment objects
        for x, y in self.base_env.mdp.get_dish_dispenser_locations():
            state.append({'id': f'dish_{x}_{y}', 'object': 'dish', 'x': x, 'y': y})

        for x, y in self.base_env.mdp.get_onion_dispenser_locations():
            state.append({'id': f'onion_{x}_{y}', 'object': 'onion', 'x': x, 'y': y})

        for x, y in self.base_env.mdp.get_tomato_dispenser_locations():
            state.append({'id': f'tomato_{x}_{y}', 'object': 'tomato', 'x': x, 'y': y})

        for x, y in self.base_env.mdp.get_serving_locations():
            state.append({'id': f'serving_{x}_{y}', 'object': 'serving pad', 'x': x, 'y': y})

        # Pots - Enhanced with pot1 and pot2 distinction
        pots = self.base_env.mdp.get_pot_states(self.base_env.state)
        pot_locations = self._get_pot_locations(pots)
        ready_pots = self._get_ready_pots(pots)
        
        # Create pot1 and pot2 based on positions (pot1 = first pot, pot2 = second pot)
        pot1_pos = pot_locations[0] if len(pot_locations) > 0 else None
        pot2_pos = pot_locations[1] if len(pot_locations) > 1 else None
        
        # Add pot1 and pot2 as distinct objects for HTN
        if pot1_pos:
            x, y = pot1_pos
            pot1_status = 'empty'
            for status in ['1_items', '2_items', '3_items', 'ready', 'cooking']:
                if pot1_pos in pots[status]:
                    pot1_status = status
                    break
            state.append({'id': 'pot1', 'object': 'pot1', 'x': x, 'y': y, 'status': pot1_status, 'position': pot1_pos})
            
        if pot2_pos:
            x, y = pot2_pos
            pot2_status = 'empty'
            for status in ['1_items', '2_items', '3_items', 'ready', 'cooking']:
                if pot2_pos in pots[status]:
                    pot2_status = status
                    break
            state.append({'id': 'pot2', 'object': 'pot2', 'x': x, 'y': y, 'status': pot2_status, 'position': pot2_pos})
        
        # Also add the original pot objects for compatibility
        for x, y in pots['empty']:
            state.append({'id': f'pot_{x}_{y}', 'object': 'pot', 'x': x, 'y': y, 'status': 'empty',
                        'onion': 0, 'tomato': 0})
        for status in ['1_items', '2_items', '3_items', 'ready', 'cooking']:
            for x, y in pots[status]:
                state.append({'id': f'pot_{x}_{y}', 'object': 'pot', 'x': x, 'y': y, 'status': status})
                
        # Add ready pots information for HTN preconditions
        for x, y in ready_pots:
            state.append({'id': f'ready_pot_{x}_{y}', 'object': 'ready_pot', 'x': x, 'y': y, 'pot_id': f'pot_{x}_{y}'})
            
        # Add ready pot1 and pot2 for HTN preconditions
        if pot1_pos and pot1_pos in ready_pots:
            state.append({'id': 'ready_pot1', 'object': 'ready_pot1', 'x': pot1_pos[0], 'y': pot1_pos[1], 'pot_id': 'pot1'})
        if pot2_pos and pot2_pos in ready_pots:
            state.append({'id': 'ready_pot2', 'object': 'ready_pot2', 'x': pot2_pos[0], 'y': pot2_pos[1], 'pot_id': 'pot2'})

        # Counter objects
        counter_objects = self.base_env.mdp.get_counter_objects_dict(self.base_env.state)
        for obj_type in counter_objects:
            for x, y in counter_objects[obj_type]:
                state.append({'id': f'{obj_type}_{x}_{y}', 'object': obj_type, 'x': x, 'y': y})

        # Empty counters are valid action targets for dropping held objects.
        for x, y in _get_empty_counter_locations(self.base_env.mdp, self.base_env.state):
            state.append({'id': f'counter_{x}_{y}',
                        'object': 'counter',
                        'x': x,
                        'y': y,
                        'status': 'empty',
                        'terrain': 'X'})

        # Terrain
        for x in range(self.base_env.mdp.width):
            for y in range(self.base_env.mdp.height):
                state.append({'id': f'terrain_{x}_{y}',
                            'terrain': self.base_env.mdp.terrain_mtx[y][x],
                            'x': x,
                            'y': y})

        # Orders
        for i, order in enumerate(self.base_env.state.all_orders):
            state.append({'id': f'order_{i}',
                        'order': str(order),
                        'onion': order._ingredients.count('onion'),
                        'tomato': order._ingredients.count('tomato')})

        # Timestep (wrap it in a dict with id)
        state.append({'id': 'timestep', 'timestep': self.base_env.state.timestep})

        return state

    def _get_pot_locations(self, pots):
        """Return list of pot (x,y) positions in consistent order (pot1, pot2, ...). Uses mdp.get_pot_locations() if available, else derived from get_pot_states."""
        if hasattr(self.base_env.mdp, 'get_pot_locations') and callable(getattr(self.base_env.mdp, 'get_pot_locations')):
            return self.base_env.mdp.get_pot_locations()
        out = []
        for status in ['empty', '1_items', '2_items', '3_items', 'ready', 'cooking']:
            for pos in pots.get(status, []):
                if pos not in out:
                    out.append(pos)
        return out

    def _get_ready_pots(self, pots):
        """Return list of (x,y) positions of ready pots. Uses mdp.get_ready_pots() if available, else pots['ready']."""
        if hasattr(self.base_env.mdp, 'get_ready_pots') and callable(getattr(self.base_env.mdp, 'get_ready_pots')):
            return self.base_env.mdp.get_ready_pots(pots)
        return list(pots.get('ready', []))

    def get_route_plan(self, target):
        pos, orr = self.get_player_pos_and_or()
        problem = OvercookedRouteProblem((self.player_id, pos, orr),
                                         goal=target, extra=self.base_env)
        try:
            sol = next(best_first_search(problem))
            return sol.path()
        except StopIteration:
            return None

    def _get_route_to_position(self, target_position):
        """
        Route to a specific position (x, y) - used for pot1/pot2 routing
        """
        pos, orr = self.get_player_pos_and_or()
        
        # Create a custom routing problem that targets a specific position
        class PositionRouteProblem(OvercookedRouteProblem):
            def __init__(self, initial_state, target_pos, extra):
                self.target_pos = target_pos
                super().__init__(initial_state, goal=None, extra=extra)
            
            def goal_test(self, state_node, goal_node=None):
                player_idx, pos, orr = state_node.state
                facing = (pos[0] + orr[0], pos[1] + orr[1])
                # Check if we're facing the target position
                return facing == self.target_pos
        
        problem = PositionRouteProblem((self.player_id, pos, orr), target_position, self.base_env)
        try:
            sol = next(best_first_search(problem))
            return sol.path()
        except StopIteration:
            print(f"[ENV] Could not find route to position {target_position}")
            return None

    def execute_action(self, action_name: str, args: List[str]) -> bool:
        if isinstance(args, tuple):
            args = list(args)
        print(f"[ENV] Executing: {action_name}({args})")

        if action_name == "drop":
            if self.base_env.state.players[self.player_id].held_object is None:
                print("[ENV] Cannot drop: player is not holding anything")
                return False
            if not self.execute_action("go to", ["counter"]):
                return False
            return self.execute_action("act", [])

        if action_name == "go to" and len(args) == 1:
            target = args[0]
            
            # Handle specific pot routing for pot1, pot2, ready_pot1, ready_pot2
            if target in ['pot1', 'pot2', 'ready_pot1', 'ready_pot2']:
                pots = self.base_env.mdp.get_pot_states(self.base_env.state)
                pot_locations = self._get_pot_locations(pots)
                
                if target in ['pot1', 'ready_pot1'] and len(pot_locations) > 0:
                    # Route to the first pot (pot1)
                    pot1_pos = pot_locations[0]
                    print(f"[ENV] Routing to pot1 at position {pot1_pos}")
                    action_plan = self._get_route_to_position(pot1_pos)
                elif target in ['pot2', 'ready_pot2'] and len(pot_locations) > 1:
                    # Route to the second pot (pot2)
                    pot2_pos = pot_locations[1]
                    print(f"[ENV] Routing to pot2 at position {pot2_pos}")
                    action_plan = self._get_route_to_position(pot2_pos)
                else:
                    # Fallback to generic pot routing
                    print(f"[ENV] Fallback: routing to generic pot for {target}")
                    action_plan = self.get_route_plan('pot')
            else:
                action_plan = self.get_route_plan(target)
            
            if action_plan is not None:
                for action in action_plan:
                    command = [(0, 0) for _ in self.base_env.state.players]
                    command[self.player_id] = action
                    self.base_env.step(command)
            else:
                print(f"[ENV] Could not find route to {target}")
                return False
        elif action_name == "wait 20min":
            for i in range(20):
                command = [(0, 0) for _ in self.base_env.state.players]
                self.base_env.step(command)
        elif action_name in ["get", "boil", "plate", "deliver", "cook"]:
            # These are high-level HTN methods, not directly executable
            return False
        else:
            command = [(0, 0) for _ in self.base_env.state.players]
            if action_name == "up":
                command[self.player_id] = (0, -1)
            if action_name == "down":
                command[self.player_id] = (0, 1)
            if action_name == "left":
                command[self.player_id] = (-1, 0)
            if action_name == "right":
                command[self.player_id] = (1, 0)
            if action_name == "act":
                command[self.player_id] = OVERCOOKED_ACT_COMMAND
                
            self.base_env.step(command)

        if self.render:
            self.render_state()

        self._pause_after_action()

        return True

if __name__ == "__main__":
    horizon = 5000
    env = OvercookedAIEnv(player_id=0, horizon=horizon, layout="bonus_order_test", action_delay_ms=200)
    env.get_state()
    actions = env.get_actions()    
    env.execute_action(action_name="go to", args=['onion'])
    env.execute_action(action_name="act", args=['onion'])
    env.execute_action(action_name="go to", args=['counter'])
    env.execute_action(action_name="act", args=['counter'])
    env.execute_action(action_name="go to", args=['onion'])
    env.execute_action(action_name="act", args=['onion'])
    env.execute_action(action_name="go to", args=['pot'])
    env.execute_action(action_name="act", args=['pot'])
    env.execute_action(action_name="act", args=['pot'])
    env.execute_action(action_name="wait 20min", args=[])
    env.execute_action(action_name="go to", args=['dish'])
    env.execute_action(action_name="act", args=['dish'])
    env.execute_action(action_name="go to", args=['pot'])
    env.execute_action(action_name="act", args=['pot'])
    env.execute_action(action_name="go to", args=['serving pad'])
    env.execute_action(action_name="act", args=['serving pad'])
    env.execute_action(action_name="go to", args=['onion'])
    env.execute_action(action_name="act", args=['onion'])
    env.execute_action(action_name="go to", args=['pot'])
    env.execute_action(action_name="act", args=['pot'])
    env.execute_action(action_name="act", args=['pot'])
    env.execute_action(action_name="wait 20min", args=[])
    env.execute_action(action_name="go to", args=['dish'])
    env.execute_action(action_name="act", args=['dish'])
    env.execute_action(action_name="go to", args=['pot'])
    env.execute_action(action_name="act", args=['pot'])
    env.execute_action(action_name="go to", args=['serving pad'])
    env.execute_action(action_name="act", args=['serving pad'])
    env.execute_action(action_name="go to", args=['onion'])
    env.execute_action(action_name="act", args=['onion'])
    env.execute_action(action_name="go to", args=['counter'])
    env.execute_action(action_name="act", args=['counter'])
    env.execute_action(action_name="go to", args=['onion'])
    env.execute_action(action_name="act", args=['onion'])
    env.execute_action(action_name="go to", args=['pot'])
    env.execute_action(action_name="act", args=['pot'])
    env.execute_action(action_name="act", args=['pot'])
    env.execute_action(action_name="wait 20min", args=[])
    env.execute_action(action_name="go to", args=['dish'])
    env.execute_action(action_name="act", args=['dish'])
    env.execute_action(action_name="go to", args=['pot'])
    env.execute_action(action_name="act", args=['pot'])
    env.execute_action(action_name="go to", args=['serving pad'])
    env.execute_action(action_name="act", args=['serving pad'])
    env.execute_action(action_name="go to", args=['onion'])
    env.execute_action(action_name="act", args=['onion'])
    env.execute_action(action_name="go to", args=['pot'])
    env.execute_action(action_name="act", args=['pot'])
    env.execute_action(action_name="act", args=['pot'])
    env.execute_action(action_name="wait 20min", args=[])
    env.execute_action(action_name="go to", args=['dish'])
    env.execute_action(action_name="act", args=['dish'])
    env.execute_action(action_name="go to", args=['pot'])
    env.execute_action(action_name="act", args=['pot'])
    env.execute_action(action_name="go to", args=['serving pad'])
    env.execute_action(action_name="act", args=['serving pad'])

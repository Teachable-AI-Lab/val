from typing import List
from typing import Tuple
import copy
from random import choice

from pprint import pprint
import pygame
import numpy as np

from overcooked_ai_py.planning.planners import MotionPlanner
from overcooked_ai_py.mdp.layout_generator import LayoutGenerator
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


# from shop2.domain import Operator
# from shop2.domain import Method
# from shop2.domain import Task
# from shop2.domain import Filter
# from shop2.fact import Fact
# from shop2.common import V

class OvercookedRouteProblem(Problem):

    def successors(self, node):
        """
        Computes successors and computes the value of the node as cost. 
        This will do something like breadth first.
        """
        # extra = self.base_env
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

        counter_objects = self.base_env.mdp.get_counter_objects_dict(self.base_env.state)
        if target in counter_objects:
            for ox, oy in counter_objects[target]:
                if ox == target[0] and oy == target[1]:
                    return True
    
        return False

class OvercookedAIEnv(AbstractEnvInterface):

    def __init__(self, player_id=0, horizon=100, layout="asymmetric_advantages", render=True):
        """
        Full list of layouts here:
        https://github.com/HumanCompatibleAI/overcooked_ai/tree/cb2e50cae95accbe4618879d88e565c87c54b1c3/src/overcooked_ai_py/data/layouts
        """
        self.layout = layout
        self.horizon = horizon
        self.player_id = player_id
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

    def render_state(self):
        surface = self.visualizer.render_state(state=self.base_env.state,
                                               grid=self.base_env.mdp.terrain_mtx,
                                               hud_data=StateVisualizer.default_hud_data(
                                                   self.base_env.state))

        rendered_width, rendered_height = surface.get_size()
        if (rendered_width, rendered_height) != self.screen.get_size():
            self.screen = pygame.display.set_mode((rendered_width, rendered_height), pygame.RESIZABLE)

        self.screen.blit(surface, (0, 0))
        pygame.display.flip()
        self.clock.tick(10)

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
                    Task('interact'),
                ]
            )
        ]
        descriptions["get"] = "Get an object by interacting with and moving to the object's location."

        domain["boil"] = [
            Method(
                name='boil',
                args=(V('object'),),
                preconditions=[],
                subtasks=[
                    Task('go to', 'pot'),
                    Task('interact')
                ]
            ),
            Method(
                name='boil',
                args=(V('object'),),
                preconditions=[],
                subtasks=[
                    Task('interact')
                ]
            ),
            Method(
                name='boil',
                args=(V('object'),),
                preconditions=[],
                subtasks=[
                    Task('go to', 'pot'),
                    Task('interact'),
                    Task('interact'),
                    Task('wait 20min')
                ]
            )
            
        ]
        descriptions["boil"] = "Boil the onion by moving to the pot and interacting with it."

        # domain["plate"] = [
        #     Method(
        #         name='plate',
        #         preconditions=(),
        #         subtasks=[
        #             Task('get', 'dish'),
        #             Task('go to', 'pot'),
        #             Task('interact')
        #         ]
        #     ),
        # ]
        # descriptions["plate"] = "Plate the soup by going to the plate area and interacting with it."
        
        domain["deliver"] = [
            Method(
                name='plate',
                preconditions=(),
                subtasks=[
                    Task('go to', 'serving pad'),
                    Task('interact')
                ]
            ),
        ]
        descriptions["deliver"] = "Go to the serving pad and interact with it to deliver the soup."
        
        ####### operators #######
        domain["go to"] = [
            Operator(
                name='go to', 
                args=(V('location'),),
                # preconditions=[Fact(type='fact', object=V('location'))],
                effects=[]
            ),
        ]
        descriptions["go to"] = "Goes to and faces the target object, where object is something like pot, onion etc."
        
        domain["interact"] = [
            Operator(
                name='interact',
                args=(),
                preconditions=[],
                effects=[]
            ),
        ]
        descriptions["interact"] = "Interact with the object, e.g., this should be called if you are trying to interact with the pot, plate, tomato, onion, etc."
            
        domain["wait 20min"] = [
            Operator(
                name='wait 20min',
                args=(),
                preconditions=(),
                effects=[]
            ),
        ]
        descriptions["wait 20min"] = "Waits for 20 time steps."

        # domain["left/0"] = [
        #     Operator(
        #         name=('left',),
        #         preconditions=(),
        #         effects=[]
        #     ),
        # ]
        # descriptions["left/0"] = "Moves one unit left."

        # domain["right/0"] = [
        #     Operator(
        #         name=('right',),
        #         preconditions=(),
        #         effects=[]
        #     ),
        # ]
        # descriptions["right/0"] = "Moves one unit right."

        # domain["up/0"] = [
        #     Operator(
        #         name=('up',),
        #         preconditions=(),
        #         effects=[]
        #     ),
        # ]
        # descriptions["up/0"] = "Moves one unit up."

        # domain["down/0"] = [
        #     Operator(
        #         name=('down',),
        #         preconditions=(),
        #         effects=[]
        #     ),
        # ]
        # descriptions["down/0"] = "Moves one unit down."

        
   
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

        # Static environment objects
        for x, y in self.base_env.mdp.get_dish_dispenser_locations():
            state.append({'id': f'dish_{x}_{y}', 'object': 'dish', 'x': x, 'y': y})

        for x, y in self.base_env.mdp.get_onion_dispenser_locations():
            state.append({'id': f'onion_{x}_{y}', 'object': 'onion', 'x': x, 'y': y})

        for x, y in self.base_env.mdp.get_tomato_dispenser_locations():
            state.append({'id': f'tomato_{x}_{y}', 'object': 'tomato', 'x': x, 'y': y})

        for x, y in self.base_env.mdp.get_serving_locations():
            state.append({'id': f'serving_{x}_{y}', 'object': 'serving pad', 'x': x, 'y': y})

        # Pots
        pots = self.base_env.mdp.get_pot_states(self.base_env.state)

        for x, y in pots['empty']:
            state.append({'id': f'pot_{x}_{y}', 'object': 'pot', 'x': x, 'y': y, 'status': 'empty',
                        'onion': 0, 'tomato': 0})
        for status in ['1_items', '2_items', '3_items', 'ready', 'cooking']:
            for x, y in pots[status]:
                state.append({'id': f'pot_{x}_{y}', 'object': 'pot', 'x': x, 'y': y, 'status': status})

        # Counter objects
        counter_objects = self.base_env.mdp.get_counter_objects_dict(self.base_env.state)
        for obj_type in counter_objects:
            for x, y in counter_objects[obj_type]:
                state.append({'id': f'{obj_type}_{x}_{y}', 'object': obj_type, 'x': x, 'y': y})

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


    def get_route_plan(self, target):
        pos, orr = self.get_player_pos_and_or()
        problem = OvercookedRouteProblem((self.player_id, pos, orr),
                                         goal=target, extra=self.base_env)
        try:
            sol = next(best_first_search(problem))
            return sol.path()
        except StopIteration:
            return None

    def execute_action(self, action_name: str, args: List[str]) -> bool:
        if isinstance(args, tuple):
            args = list(args)
        print(f"[ENV] Executing: {action_name}({args})")

        if action_name == "go to" and len(args) == 1:
            action_plan = self.get_route_plan(args[0])
            for action in action_plan:
                command = [(0, 0) for _ in self.base_env.state.players]
                command[self.player_id] = action
                self.base_env.step(command)
        elif action_name == "wait 20min":
            for i in range(20):
                command = [(0, 0) for _ in self.base_env.state.players]
                self.base_env.step(command)

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
            if action_name == "interact":
                command[self.player_id] = 'interact'
                
            self.base_env.step(command)

        if self.render:
            self.render_state()

        return True

if __name__ == "__main__":
    horizon = 100
    env = OvercookedAIEnv(player_id=0, horizon=horizon)
    #for i in range(horizon):
    env.get_state()
    actions = env.get_actions()
    env.execute_action(action_name="go to", args=['pot'])
    env.execute_action(action_name="interact", args=['pot'])
    env.execute_action(action_name="interact", args=['pot'])
    env.execute_action(action_name="wait20", args=[])
    
    env.execute_action(action_name="go to", args=['onion'])
    env.execute_action(action_name="interact", args=['onion'])
    env.execute_action(action_name="go to", args=['pot'])
    env.execute_action(action_name="interact", args=['pot'])
    
    env.execute_action(action_name="interact", args=['pot'])
    env.execute_action(action_name="wait20", args=[])
    env.execute_action(action_name="interact", args=['pot'])

    env.execute_action(action_name="interact", args=['pot'])
    env.execute_action(action_name="wait20", args=[])
    env.execute_action(action_name="go to", args=['dish'])
    env.execute_action(action_name="interact", args=['dish'])
    env.execute_action(action_name="go to", args=['pot'])
    env.execute_action(action_name="interact", args=['pot'])
    env.execute_action(action_name="go to", args=['serving pad'])
    env.execute_action(action_name="interact", args=['serving pad'])

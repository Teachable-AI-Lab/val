from typing import List
from typing import Tuple
import copy
from random import choice

from pprint import pprint
import pygame
import numpy as np

from overcooked_ai_py.mdp.overcooked_env import OvercookedEnv
from overcooked_ai_py.mdp.overcooked_mdp import OvercookedGridworld
from overcooked_ai_py.visualization.state_visualizer import StateVisualizer

from val.env_interfaces.abstract_interface import AbstractEnvInterface


class OvercookedAIEnv(AbstractEnvInterface):

    def __init__(self, player_id=0, horizon=100, render=True):

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
        self.mdp = OvercookedGridworld.from_layout_name("asymmetric_advantages")
        self.base_env = OvercookedEnv.from_mdp(self.mdp, horizon=self.horizon)

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
        return [
                {"name": "wait",
                 "args": [],
                 "description": "waits and does nothing",
                 "preconditions": []
                 },
                {"name": "left",
                 "args": [],
                 "description": "Moves one unit left",
                 "preconditions": []
                 },
                {"name": "right",
                 "args": [],
                 "description": "Moves one unit right",
                 "preconditions": []
                 },
                {"name": "up",
                 "args": [],
                 "description": "Moves one unit up",
                 "preconditions": []},
                {"name": "down",
                 "args": [],
                 "description": "Moves one unit down",
                 "preconditions": []},
                {"name": "interact",
                 "args": [],
                 "description": "presses the space bar to interact",
                 "preconditions": []}
                ]

    def get_state(self) -> dict:
        state = []

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

            state.append({'object': 'player',
                          'player_index': i,
                          'x': player.position[0],
                          'y': player.position[1],
                          'orientation': orientation,
                          'is_me': str(i == self.player_id),
                          'holding': player.held_object})

        for x, y in self.base_env.mdp.get_dish_dispenser_locations():
            state.append({'object': 'dish_dispenser', 'x': x, 'y': y})

        for x, y in self.base_env.mdp.get_onion_dispenser_locations():
            state.append({'object': 'onion_dispenser', 'x': x, 'y': y})

        for x, y in self.base_env.mdp.get_tomato_dispenser_locations():
            state.append({'object': 'tomato_dispenser', 'x': x, 'y': y})

        for x, y in self.base_env.mdp.get_serving_locations():
            state.append({'object': 'serving_pad', 'x': x, 'y': y})

        pots = self.base_env.mdp.get_pot_states(self.base_env.state)

        for x, y in pots['empty']:
            state.append({'object': 'pot', 'x': x, 'y': y, 'status': 'empty',
                          'onion': 0, 'tomato': 0})
        for x, y in pots['1_items']:
            state.append({'object': 'pot', 'x': x, 'y': y, 'status': '1_items'})
        for x, y in pots['2_items']:
            state.append({'object': 'pot', 'x': x, 'y': y, 'status': '2_items'})
        for x, y in pots['3_items']:
            state.append({'object': 'pot', 'x': x, 'y': y, 'status': '3_items'})
        for x, y in pots['ready']:
            state.append({'object': 'pot', 'x': x, 'y': y, 'status': 'ready'})
        for x, y in pots['cooking']:
            state.append({'object': 'pot', 'x': x, 'y': y, 'status': 'cooking'})

        counter_objects = self.base_env.mdp.get_counter_objects_dict(self.base_env.state)
        for obj_type in counter_objects:
            for x, y in counter_objects[obj_type]:
                state.append({'object': obj_type, 'x': x, 'y': y})

        for x in range(self.base_env.mdp.width):
            for y in range(self.base_env.mdp.height):
                state.append({'terrain': self.base_env.mdp.terrain_mtx[y][x],
                              'x': x,
                              'y': y})

        for order in self.base_env.state.all_orders:
            state.append({'order': str(order),
                          'onion': order._ingredients.count('onion'),
                          'tomato': order._ingredients.count('tomato')})

        state.append({'timestep': self.base_env.state.timestep})        

        # pprint(state) 
        return state

    def execute_action(self, action_name: str, args: List[str]) -> bool:
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
        if action_name == "wait":
            command[self.player_id] = (0, 0)

        self.base_env.step(command)

        if self.render:
            self.render_state()

        return True

if __name__ == "__main__":

    horizon = 500
    env = OvercookedAIEnv(player_id=1, horizon=horizon)
    for i in range(horizon):
        env.get_state()
        actions = env.get_actions()
        action = choice(actions)
        env.execute_action(action_name=action['name'], args=[])
        env.render_state()

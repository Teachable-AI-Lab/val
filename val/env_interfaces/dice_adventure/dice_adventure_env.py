from json import loads
from typing import List
from typing import Tuple
from val.env_interfaces.abstract_interface import AbstractEnvInterface
from val.env_interfaces.dice_adventure.game.dice_adventure_python_env import DiceAdventurePythonEnv
from val.env_interfaces.dice_adventure.move_planner import MovePlanner

import os
import json


class DiceAdventureEnv(AbstractEnvInterface):

    def __init__(self, player="Dwarf", server="local", state_version="fow"):
        self.player = player
        self.env = DiceAdventurePythonEnv(player=player, server=server, state_version=state_version)
        self.env.register(self.player)
        self.move_planner = MovePlanner()
        base_dir = os.path.dirname(os.path.abspath(__file__))
        actions_path = os.path.join(base_dir, "env_actions.json")
        with open(actions_path, "r") as file:
            self.actions = json.load(file)

    def get_objects(self) -> List[str]:
        state = self.env.get_state()
        char_map = {"C11": "Dwarf", "C21": "Giant", "C31": "Human"}
        objects = [f'{ele["entityType"]}-{ele["id"]}' for ele in state["content"]["scene"]]
        for id_, char in char_map.items():
            for i in range(len(objects)):
                if objects[i].split("-")[1] == id_:
                    objects[i] = f"{char}-{id_}"
                    break
        return objects

    def get_actions(self) -> List[Tuple[str, List[str]]]:
        """
        Returns actions in a format the HTN interface can create primitives.
        """
        return self.actions

    def get_state(self) -> list:
        """
        Returns the state in a list that can be converted into HTN representation.
        """
        state = self.env.get_state()
        for ele in state["content"]["scene"]:
            for k in ele:
                if isinstance(ele[k], list):
                    ele[k] = ",".join(ele[k])
                    
        return [state["content"]["gameData"]] + state["content"]["scene"]

    def execute_action(self, action_name: str, args: List[str]) -> bool:
        """
        Takes an action and its arguments and executes it in the environment.
        """
        state = self.env.get_state()
        player_obj = self.find_obj_by_id(state, self.env.get_player_code(self.player) + "1")
        if action_name == "move_to":
            if len(args) == 1:
                target_pos = self.get_target_pos(args[0], state)
                self.move_to_target(target_pos, player_obj, state)
            elif len(args) == 2:
                self.move_in_direction(args[0], int(args[1]), player_obj, state)
            elif len(args) == 3:
                target_pos = self.get_target_pos(args[0], state)
                tx, ty = self.change_position(target_pos, args[1], int(args[2]))
                self.move_to_target((tx, ty), player_obj, state)
            return True
        else:
            next_state = self.env.execute_action(player=self.player, game_action=action_name)
            self.env.render()
            return next_state["status"] != "ILLEGAL_ACTION"

    def move_in_direction(self, direction, num_steps, player_obj, state):
        target_x, target_y = self.change_position((player_obj["x"], player_obj["y"]), direction, num_steps)
        self.move_to_target((target_x, target_y), player_obj, state)

    @staticmethod
    def change_position(pos, direction, num_steps):
        x, y = pos
        if direction == "left":
            x -= num_steps
        elif direction == "right":
            x += num_steps
        elif direction == "up":
            y += num_steps
        elif direction == "down":
            y -= num_steps
        return x, y

    def move_to_target(self, target_pos, player_obj, state):
        while player_obj["actionPoints"] > 0:
            px, py = self.get_x_y_cursor(player_obj["x"], player_obj["y"], player_obj["actionPlan"])
            action = self.get_next_move_action((px, py), target_pos, state)
            if action is None:
                break
            state = self.env.execute_action(player=self.player, game_action=action)
            player_obj = self.find_obj_by_id(state, self.env.get_player_code(self.player) + "1")
        self.env.execute_action(player=self.player, game_action="submit")

    def get_target_pos(self, target, state):
        target_id = target.split("-")[-1].strip()
        # Convert character names to Ids if needed
        if target_id in self.env.get_player_names():
            target_id = self.env.get_player_code(target_id) + "1"
        target_obj = self.find_obj_by_id(state, target_id)
        return target_obj["x"], target_obj["y"]

    @staticmethod
    def get_x_y_cursor(x, y, action_plan):
        for action in action_plan:
            action = action.lower()
            if action == "up":
                y += 1
            elif action == "down":
                y -= 1
            elif action == "left":
                x -= 1
            elif action == "right":
                x += 1
            elif action == "wait":
                pass
        return x, y

    def get_next_move_action(self, src, dest, state):
        return self.move_planner.get_next_move(src, dest, state)[0]

    @staticmethod
    def find_obj_by_id(state, obj_id):
        for obj in state["content"]["scene"]:
            if obj.get("id") == obj_id:
                return obj


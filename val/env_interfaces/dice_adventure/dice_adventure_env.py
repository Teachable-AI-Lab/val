from json import loads
from typing import List
from typing import Tuple
from val.env_interfaces.abstract_interface import AbstractEnvInterface
from val.env_interfaces.dice_adventure.game.dice_adventure_python_env import DiceAdventurePythonEnv

import os
import json


class DiceAdventureEnv(AbstractEnvInterface):

    def __init__(self, player="Dwarf", server="local"):
        self.player = player
        self.env = DiceAdventurePythonEnv(player=player, server=server)
        #self.actions = loads(open("../val/env_interfaces/dice_adventure/env_actions.json").read())
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
                    objects[i] += f"-{char}"
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
        next_state = self.env.execute_action(player=self.player, game_action=action_name)
        self.env.render()
        return next_state["status"] != "ILLEGAL_ACTION"

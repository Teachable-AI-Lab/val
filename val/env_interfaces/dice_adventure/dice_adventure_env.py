from json import loads
from typing import List
from typing import Tuple
from val.env_interfaces.abstract_interface import AbstractEnvInterface
from val.env_interfaces.dice_adventure.game.dice_adventure_python_env import DiceAdventurePythonEnv


class DiceAdventureEnv(AbstractEnvInterface):

    def __init__(self, player="Dwarf", server="local"):
        self.player = player
        self.env = DiceAdventurePythonEnv(player=player, server=server)
        self.actions = loads(open("../val/env_interfaces/dice_adventure/env_actions.json").read())

    def get_objects(self) -> List[str]:
        state = self.env.get_state()
        return [f'{ele["entityType"]}-{ele["id"]}' for ele in state["content"]["scene"]]

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
        return state["content"]["gameData"] + state["content"]["scene"]

    def execute_action(self, action_name: str, args: List[str]) -> bool:
        """
        Takes an action and its arguments and executes it in the environment.
        """
        next_state = self.env.execute_action(player=self.player, game_action=action_name)
        self.env.render()
        return next_state["status"] != "ILLEGAL_ACTION"

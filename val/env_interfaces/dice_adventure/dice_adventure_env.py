from json import loads
from typing import List
from typing import Tuple
from game.dice_adventure_python_env import DiceAdventurePythonEnv


class DiceAdventureEnv:

    def __init__(self, server="local"):
        self.env = DiceAdventurePythonEnv(server=server)
        self.actions = loads(open("game_actions_env.json").read())

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
        self.env.execute_action(player=args[0], game_action=action_name)
        return True

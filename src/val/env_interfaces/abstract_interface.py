from typing import List
from typing import Tuple


class AbstractEnvInterface:

    def get_objects(self) -> List[str]:
        raise NotImplementedError("Not implemented yet")

    def get_actions(self) -> List[Tuple[str, List[str]]]:
        """
        Returns actions in a format the HTN interface can create primitives.
        """
        raise NotImplementedError("Not implemented yet")

    def get_state(self) -> dict:
        """
        Returns the state in a dict that can be converted into HTN representation.
        """
        raise NotImplementedError("Not implemented yet")

    def execute_action(self, action_name: str, args: List[str]) -> bool:
        """
        Takes an action and its arguments and executes it in the environment.
        """
        raise NotImplementedError("Not implemented yet")

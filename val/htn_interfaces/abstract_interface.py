from typing import Any, List

from pyhtn.domain.task import NetworkTask
from pyhtn.conditions.fact import Fact
from val.agent import V

class AbstractHtnInterface:

    def __init__(self, agent):
        """
        Needs agent.
        """
        self.agent = agent

    def get_tasks(self) -> List[NetworkTask]:
        """
        Return a list of ungrounded tasks (no repeats).
        """
        raise NotImplementedError("Not implemented yet")

    def execute_task(self, task: Any) -> bool:
        """
        Executes the task provided in the environment
        """
        raise NotImplementedError("Not implemented yet")

    def add_method(self,
                   task_name: str,
                   task_args: List[V],
                   preconditions: Fact,
                   subtasks: List[NetworkTask],
                   state: List[dict]):
        """
        Creates a new HTN method and adds to domain.
        """
        raise NotImplementedError("Not implemented yet")
        

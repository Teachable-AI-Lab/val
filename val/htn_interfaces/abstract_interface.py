from typing import List

from val.agent import Task
from val.agent import V

class AbstractHtnInterface:

    def __init__(self, agent):
        """
        Needs agent.
        """
        raise NotImplementedError("Not implemented yet")

    def get_tasks(self) -> List[Task]:
        """
        Return a list of ungrounded tasks (no repeats).
        """
        raise NotImplementedError("Not implemented yet")

    def execute_task(self, task: Task) -> bool:
        """
        Executes the task provided in the environment
        """
        raise NotImplementedError("Not implemented yet")

    def add_method(task_name: str, task_args: List[V], subtasks: List[Task]):
        """
        Creates a new HTN method and adds to domain.
        """
        raise NotImplementedError("Not implemented yet")
        

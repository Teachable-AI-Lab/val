from typing import List
from shop2.domain import Task
from shop2.common import V


class AbstractHtnInterface:

    def __init__(self, *args, **kwargs):
        """
        Needs both env and user interfaces so it can execute in the world and
        confirm execution.
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
        


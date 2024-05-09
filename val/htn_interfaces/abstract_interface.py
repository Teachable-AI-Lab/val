from typing import List
from shop2.domain import Method, Operator
from agent import Task
from agent import V
from shop2.planner import planner

from env_interfaces import AbstractEnvInterface
from shop2.fact import Fact


def dict_to_facts(data: dict) -> Fact:
    state = Fact(start=True)
    for fact in data['state']:
        state = state & Fact(**{key: (V(value[1:]) if (isinstance(value, str) and value[0] == '?') else value) 
                                for key, value in fact.items()})
    return state

class AbstractHtnInterface:

    def __init__(self, *args, **kwargs):
        """
        Needs both env and user interfaces so it can execute in the world and
        confirm execution.
        """
        self.state = dict_to_facts(args[0])
        self.domain = args[1]
        self.task = args[2]
        raise NotImplementedError("Not implemented yet")

    def get_tasks(self) -> List[Task]:
        """
        Return a list of ungrounded tasks (no repeats).
        """
        if result := planner(self.state, self.domain, self.task):
            plan, state = result
            return plan
        return []
        
        # raise NotImplementedError("Not implemented yet")

    def execute_task(self, task: Task, env: AbstractEnvInterface) -> bool:
        """
        Executes the task provided in the environment
        """

        if result := planner(self.state, self.domain, self.task):
            plan, state = result
        for action in plan:
            if not env.execute_action(action.name, action.args, action.preconditions):
                return False
        return True
        # raise NotImplementedError("Not implemented yet")

    def add_method(self, task_name: str, task_args: List[V], preconditions: [Fact], subtasks: List[Task]):
        """
        Creates a new HTN method and adds to domain.
        """
        action = Method(head=(task_name, *task_args), preconditions=preconditions, subtasks=subtasks)
        self.domain.setdefault(task_name, []).append(action)
        raise NotImplementedError("Not implemented yet")
    




        


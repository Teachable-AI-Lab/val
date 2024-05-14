from typing import List
from collections import defaultdict
from collections import deque

from shop2.domain import Operator
from shop2.domain import Method
# from shop2.planner import planner
from shop2.fact import Fact
# from shop2.common import FailedPlanException
from shop2.conditions import AND

from val.utils import Task
from val.utils import V
from val.htn_interfaces.abstract_interface import AbstractHtnInterface
from val.env_interfaces.abstract_interface import AbstractEnvInterface
# from user_interfaces.abstract_interface import AbstractUserInterface


def dict_to_operators(operator_dict_list: list) -> List[Operator]:
    primitives = set()

    for operator_dict in operator_dict_list:
        primitives.add(Task(operator_dict['name'], tuple([V(arg) for arg in operator_dict["args"]])))

    return primitives

class BasicHtnInterface(AbstractHtnInterface):

    def __init__(self, env: AbstractHtnInterface,
                 # user_interface: AbstractUserInterface
                 ):
        """
        Needs both env and user interfaces so it can execute in the world and
        confirm execution.
        """
        self.env = env
    
        # TODO consider how and in what way we need the user interface
        # self.user_interface = user_interface
        self.primitives = dict_to_operators(env.get_actions())
        self.methods = {}

    def get_tasks(self) -> List[Task]:
        """
        Return a list of ungrounded tasks (no repeats).
        """
        tasks = [t for t in self.primitives] + [t for t in self.methods]
        tasks = list(set(tasks))
        return tasks
        
    def execute_task(self, task: Task) -> bool:
        """
        Executes the task provided in the environment
        """
        queue = deque([task])

        while len(queue) > 0:
            task = queue.popleft()

            if task in self.primitives:
                if not self.env.execute_action(task.name, task.args):
                    return False

            elif task in self.methods:
                queue.extend(self.methods[task])

        return True

    def add_method(self, task_name: str,
                   task_args: List[V], preconditions: Fact, subtasks: List[Task]):
        """
        Creates a new HTN method and adds to domain.
        """
        task = Task(task_name, tuple(task_args))
        self.methods[task] = subtasks

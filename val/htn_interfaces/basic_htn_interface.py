from typing import List
from collections import defaultdict
from collections import deque

from shop2.domain import Operator
from shop2.domain import Method
from shop2.domain import unify
from shop2.domain import subst
from shop2.fact import Fact

from shop2.domain import Task
from shop2.common import V
from val.htn_interfaces.abstract_interface import AbstractHtnInterface


def dict_to_operators(operator_dict_list: list) -> List[Operator]:
    primitives = {}

    for operator_dict in operator_dict_list:
        key = f"{ operator_dict['name'] }/{ len(operator_dict['args']) }"
        primitives[key] = (Task(operator_dict['name'],
                               *[V(arg) for arg in operator_dict["args"]]),
                           operator_dict['description'])

    return primitives

class BasicHtnInterface(AbstractHtnInterface):

    def __init__(self, agent):
        """
        Needs both env and user interfaces so it can execute in the world and
        confirm execution.
        """
        self.agent = agent
        self.primitives = dict_to_operators(self.agent.env.get_actions())
        self.methods = defaultdict(list)

    def get_tasks(self) -> List[Task]:
        """
        Return a list of ungrounded tasks (no repeats).
        """
        tasks = [self.primitives[key] for key in self.primitives]
        # TODO the empty string here is a missing description
        tasks += [(task, "") for key in self.methods for task, _ in self.methods[key]]
        tasks = list(set(tasks))
        return tasks

    def execute_task(self, task: Task) -> bool:
        """
        Executes the task provided in the environment
        """
        queue = deque([task])

        while len(queue) > 0:
            task = queue.popleft()

            success = False

            key = f"{ task.name }/{ len(task.args) }"
            print(f"solving { task } (key={ key })")
            print(f"Primitives: { self.primitives }")
            print(f"Methods: { self.methods }")

            if key in self.primitives and self.agent.confirm_task_execution(task):
                success = self.agent.env.execute_action(task.name, task.args)

            if not success and key in self.methods:
                for ungrounded_task, ungrounded_subtasks in self.methods[key]:
                    theta = unify((task.name, *task.args),
                                  (ungrounded_task.name, *[v.to_unify_str() for v in ungrounded_task.args]))
                    print('unifying', (task.name, *task.args), 'with',
                          (ungrounded_task.name, *[v.to_unify_str() for v in ungrounded_task.args]))
                    print("theta", theta)

                    grounded_subtasks = [Task(t.name,
                                              subst(theta, tuple([v.to_unify_str() if isinstance(v, V) else v for v in t.args])))
                                         for t in ungrounded_subtasks]

                    if self.agent.confirm_task_decomposition(task, grounded_subtasks):
                        queue.extend(grounded_subtasks)
                        success = True
                        break

            if not success:
                grounded_subtasks = list(self.agent.add_method_from_task(task))
                for subtask in reversed(grounded_subtasks):
                    queue.appendleft(subtask)

        return True

    def add_method(self, task_name: str,
                   task_args: List[V], preconditions: Fact, subtasks: List[Task]):
        """
        Creates a new HTN method and adds to domain.
        """
        # TODO add descriptions to new methods.
        key = f"{ task_name }/{ len(task_args) }"
        task = Task(task_name, tuple(task_args))
        self.methods[key].append((task, subtasks))

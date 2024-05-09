from typing import List
from collections import defaultdict

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


def dict_to_facts(fact_dict_list: list) -> Fact:
    state = []
    for fact_dict in fact_dict_list:
        state.append(Fact(**{key: value for key, value in fact_dict.items()}))

    return AND(state)

def dict_to_operators(operator_dict_list: list) -> List[Operator]:
    domain = defaultdict(list)

    for operator_dict in operator_dict_list:
        head = (operator_dict['name'], *[V(arg) for arg in operator_dict["args"]])
        preconditions = []
        for precondition_dict in operator_dict['preconditions']:
            if precondition_dict['type'] == 'fact':
                # print(precondition_dict.items())
                f = Fact(**{key: (V(value[1:])
                                  if (isinstance(value, str) and len(value) > 1 and value[0] == '?') else value)
                            for key, value in precondition_dict.items() if key != 'type'})
                preconditions.append(f)
            if precondition_dict['type'] == 'filter':
                f = Filter(eval(precondition_dict['lambda']))
                preconditions.append(f)
            if precondition_dict['type'] == 'bind':
                raise NotImplementedError("Not implemented yet")

        # TODO remove effects from operator, it will just return the operator name and args
        domain[head].append(Operator(head, AND(preconditions), []))

    return domain

class PyHtnInterface(AbstractHtnInterface):

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
        self.domain = dict_to_operators(env.get_actions())

    def get_tasks(self) -> List[Task]:
        """
        Return a list of ungrounded tasks (no repeats).
        """
        # TODO do we need the var symbols? or is it just the var name?
        return list(set([Task(operator.head[0], tuple([v.name for v in operator.head[1:]]))
                         for ele in self.domain for operator in self.domain[ele]]))
        
    def execute_task(self, task: Task, env: AbstractEnvInterface) -> bool:
        """
        Executes the task provided in the environment
        """
        # TODO REMOVE THIS!!!!!
        return False

        # TODO implement planner coroutine functionality
        plan_coroutine = planner(dict_to_facts(self.env.get_state()),
                                 self.task,
                                 self.domain)

        # this should return an action (name and args) for the env to execute
        try:
            for action_name, action_args in plan_coroutine:
                success = self.env.execute_action(action_name, action_args)
                plan_couroutine.send(success, dict_to_facts(self.env.get_state()))
            return True

        # TODO implement failed plan exception
        except FailedPlanException:
            return False


    def add_method(self, task_name: str,
                   task_args: List[V], preconditions: Fact, subtasks: List[Task]):
        """
        Creates a new HTN method and adds to domain.
        """
        head = (task_name, *task_args)

        # TODO make a method a single precondition subtask pair.
        new_method = Method(head=(task_name, *task_args),
                            preconditions=preconditions, subtasks=subtasks)
        self.domain[head].append(new_method)
    




        


from typing import List
from collections import defaultdict

from shop2.domain import Operator
from shop2.domain import Method
from shop2.domain import flatten
from shop2.planner import planner
from shop2.planner import FailedPlanException, StopException
from shop2.fact import Fact
from shop2.common import V
# from shop2.common import FailedPlanException
from shop2.conditions import AND, Filter
from py_plan.unification import unify
from py_plan.unification import subst

from shop2.domain import Task
from val.htn_interfaces.abstract_interface import AbstractHtnInterface
from val.env_interfaces.abstract_interface import AbstractEnvInterface
# from user_interfaces.abstract_interface import AbstractUserInterface


def dict_to_facts(fact_dict_list: list) -> Fact:
    state = []
    for fact_dict in fact_dict_list:
        state.append(Fact(**{key: value for key, value in fact_dict.items()}))

    return AND(*state)

def dict_to_operators(operator_dict_list: list) -> List[Operator]:
    domain = defaultdict(list)
    task_descriptions = {}

    for operator_dict in operator_dict_list:
        head = (operator_dict['name'], *[V(arg[1:]) if len(arg)>1 and arg[0]=='?' else arg for arg in operator_dict["args"]])
        preconditions = []
        for precondition_dict in operator_dict['preconditions']:
            if precondition_dict['type'] == 'fact':
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
        new_operator = Operator(head, AND(*flatten(preconditions)), [])
        key = f"{ new_operator.name }/{ len(new_operator.args) }"
        domain[key].append(new_operator)
        task_descriptions[key] = operator_dict['description']
    print("DOMAIN CREATED\n", domain)
    return domain, task_descriptions

class PyHtnInterface(AbstractHtnInterface):

    def __init__(self, agent):
        """
        Needs both env and user interfaces so it can execute in the world and
        confirm execution.
        """
        self.agent = agent
    
        # TODO consider how and in what way we need the user interface
        # self.user_interface = user_interface
        self.domain, self.task_description = dict_to_operators(self.agent.env.get_actions())


    def get_tasks(self) -> List[Task]:
        """
        Return a list of ungrounded tasks (no repeats).
        """
        return list(set([(Task(operator.head[0],
                               *[v for v in operator.head[1:]]), self.task_description[key])
                         for key in self.domain for operator in self.domain[key]]))
        # return list(set([Task(operator.head[0], tuple([v for v in operator.head[1:]]))
        #                  for ele in self.domain for operator in self.domain[ele]]))
        
    def execute_task(self, task: Task) -> bool:
        """
        Executes the task provided in the environment
        """
        # # TODO REMOVE THIS!!!!!
        # return False

        # TODO implement planner coroutine functionality
        plan_coroutine = planner(dict_to_facts(self.agent.env.get_state()),
                                 [task], self.domain)

        try: 
            action_name, action_args = plan_coroutine.send(None)
            success = self.agent.env.execute_action(action_name, action_args)
            while True:
                action_name, action_args = plan_coroutine.send((success, dict_to_facts(self.agent.env.get_state())))
                # print(actio_name, action_args)
                success = self.agent.env.execute_action(action_name, action_args)
        except StopException as e: 
            return True
        except FailedPlanException as e:
            print(e)
            return False
        # this should return an action (name and args) for the env to execute
        # print("EXECUTING TASK", task)
        # try:
        #     for action_name, action_args in plan_coroutine:
        #         success = self.agent.env.execute_action(action_name, action_args)
        #         print(f"DEBUG {action_name}, {action_args}, {success}")
        #         plan_coroutine.send((success, dict_to_facts(self.agent.env.get_state())))
        #     return True
        # except FailedPlanException as e:
        #     print(e)
        #     return False


    def add_method(self, task_name: str,
                   task_args: List[V], preconditions: Fact, subtasks: List[Task]):
        """
        Creates a new HTN method and adds to domain.
        """
        # head = (task_name, *task_args)
        # TODO if we want to support it we have to convert all variables to SV
        if preconditions is None:
            raise NotImplementedError("Preconditions not supported")
        
        # TODO make a method a single precondition subtask pair.
        new_method = Method(head=(task_name, *[V(x.name) if isinstance(x, V) else x for x in task_args]),
                            preconditions=preconditions, subtasks=subtasks)
        
        key = f"{ task_name }/{ len(task_args)}"
        self.domain[key].append(new_method)
        self.task_description[key] = ""

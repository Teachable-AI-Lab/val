from typing import Any
from typing import List
from typing import Optional

from pyhtn.conditions.fact import Fact
from pyhtn.conditions.pattern_matching import AND
from pyhtn.conditions.pattern_matching import Filter
from pyhtn.conditions.pattern_matching import flatten
from pyhtn.domain.operators import NetworkOperator
from pyhtn.domain.task import NetworkTask
from pyhtn.domain.variable import V
from pyhtn.planner.planner import HtnPlanner

from val.env_interfaces.abstract_interface import AbstractEnvInterface
from val.htn_interfaces.abstract_interface import AbstractHtnInterface
from val.htn_interfaces.method_application import MethodApplication

from typing import List
from collections import defaultdict


class PyHtnInterface(AbstractHtnInterface):

    def __init__(self, agent, environment: AbstractEnvInterface):
        """
        Needs both env and user interfaces so it can execute in the world and
        confirm execution.
        """
        super().__init__(agent)
        self.env = environment
    
        # TODO consider how and in what way we need the user interface
        # self.user_interface = user_interface
        self.task_description = {}
        self.domain, self.task_descriptions = self.agent.env.get_actions()
        # initial state, authored HTN is passed to the planner
        self.planner = HtnPlanner(domain=self.domain, env=self.env)


    def get_tasks(self) -> list[tuple[NetworkTask, Any]]:
        """
        Return a list of ungrounded tasks (no repeats).
        """
        # return self.domain, self.task_descriptions
        return list(
                    set(
                        [
                         (
                            NetworkTask(method.head[0],
                            list(method.head[1:])), self.task_descriptions[key]
                         )
                         for key in self.domain for method in self.domain[key]
                        ]
                    )
        )
        # head is defined in pyHTN, self.head = (self.name, *self.args)
        # return list(set([Task(operator.head[0], tuple([v for v in operator.head[1:]]))
        #                  for ele in self.domain for operator in self.domain[ele]]))

    """
    def execute_task(self, task: Any) -> bool:
        
        # Executes the task provided in the environment
        
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
    """

    def add_method(self,
                   task_name: str,
                   task_args: List[V],
                   preconditions: Fact,
                   subtasks: List[NetworkTask],
                   state: List[dict]):
        """
        Creates a new HTN method and adds to domain.
        """
        # head = (task_name, *task_args)
        # TODO if we want to support it we have to convert all variables to SV
        if preconditions is None:
            raise NotImplementedError("Preconditions not supported")
        
        # TODO make a method a single precondition subtask pair.
        task_args = tuple(V(x.name) if isinstance(x, V) else x for x in task_args)
        new_method = self.planner.add_method(task_name, task_args, preconditions, subtasks)
        self.domain = self.planner.domain_network

        return MethodApplication(method=new_method, match=task_args, state=state)

    def add_tasks(self, tasks):
        self.planner.add_tasks(tasks)

    def get_next_method_application(self, all_methods: bool = False):
        state = self.agent.env.get_state()
        task, methods = self.planner.get_next_method_application(all_methods)
        #generate hash by deal methodAapplication.id in web interface
        return task, MethodApplication(method=methods[0], match=task.args, state=state)
        return task, [MethodApplication(method=method, match=task.args, state=state) for method in methods]
    
    def apply_method_application(self, task, method_to_apply: Any):
        self.planner.apply_method_application(task, method_to_apply)

def dict_to_facts(fact_dict_list: list) -> AND:
    state = []
    for fact_dict in fact_dict_list:
        state.append(Fact(**{key: value for key, value in fact_dict.items()}))

    return AND(*state)

def dict_to_operators(operator_dict_list: list) -> List[NetworkOperator]:
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
        new_operator = NetworkOperator(name=head[0],
                                       args=head[1:],
                                       preconditions=AND(*flatten(preconditions)),
                                       effects=[])
        key = f"{ new_operator.name }/{ len(new_operator.args) }"
        domain[key].append(new_operator)
        task_descriptions[key] = operator_dict['description']
    print("DOMAIN CREATED\n", domain)
    return domain, task_descriptions
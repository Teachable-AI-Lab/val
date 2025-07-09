from typing import List, Dict, Any
from typing import Optional

from val.utils import load_prompt
from val.utils import task_to_gpt_str

from pyhtn.htn import Task, Method, Operator, TaskEx, MethodEx, OperatorEx
from pyhtn.conditions.fact import Fact
from pyhtn.conditions.conditions import NOT
from pyhtn.domain.variable import V
from pyhtn.exceptions import FailedPlanException


from val.gpt_completer import GPTCompleter
from val.user_interfaces.abstract_interface import AbstractUserInterface
from val.env_interfaces.abstract_interface import AbstractEnvInterface
from val.htn_interfaces.abstract_interface import AbstractHtnInterface
from val.logging_system import ValLogger, EventType


class ValAgent:

    def __init__(self,
                 env: AbstractEnvInterface,
                 user_interface_class,
                 htn_interface_class,
                 openai_key: str):

        self.segment_prompt = load_prompt("prompts/chat_segmenter.txt")
        self.name_prompt = load_prompt('prompts/chat_namer.txt')
        self.gen_prompt = load_prompt('prompts/chat_gen.txt')
        self.para_prompt = load_prompt('prompts/chat_paraphrase_ider.txt')
        self.verb_prompt = load_prompt('prompts/chat_verbalizer.txt')
        self.map_prompt = load_prompt('prompts/chat_map.txt')
        self.ground_prompt = load_prompt('prompts/chat_ground.txt')

        self.gpt = GPTCompleter(openai_key)

        self.user_interface = user_interface_class()
        self.env = env
        self.htn_interface = htn_interface_class(self, self.env)
        
        # Initialize logging system
        self.logger = ValLogger()
        self.logger.start_session(
            environment_type=type(env).__name__,
            user_interface_type=user_interface_class.__name__,
            htn_interface_type=htn_interface_class.__name__
        )

    def start(self):
        while True:

            # Get current task node from planner and pass this to the user interface
            tasks = [self.verbalize_gpt(t, [arg.name for arg in t.args])
                                        for t, _ in self.htn_interface.get_tasks()]
            self.user_interface.display_known_tasks(tasks)

            user_tasks = self.user_interface.request_user_task()

            self.logger.log_event(
                EventType.USER_TASK_REQUEST,
                {"user_task": user_tasks},
                self._get_env_state_dict(),
                self._get_htn_knowledge_base_dict()
            )
            
            tasks = [task for task in self.interpret(user_tasks)]
            print(f"Tasks: {tasks}")
            
            task_dicts = [{"name": task.name, "arguments": task.args} for task in tasks]
            self.logger.log_event(
                EventType.HTN_TASK_ADDITION,
                {"tasks": task_dicts},
                self._get_env_state_dict(),
                self._get_htn_knowledge_base_dict()
            )
            
            # planner = self.htn_interface.get_planner(tasks)
            self.htn_interface.add_tasks(tasks)
            #task here is a list of dicts. eg [{'name': 'moveTo', 'arguments': ['onion']}] 

            user_choice = None

            try:
                while True:
                    if self.user_interface.check_for_break():
                        break

                    # Plan through HTN until next non-primitive task.
                    trace = self.htn_interface.plan_to_next_decomposition()
                    print("TRACE")
                    trace.print_trace()

                    if(self.htn_interface.is_exhausted()):
                        break

                    # Get the method executions considered by the planner
                    task_exec, method_execs = self.htn_interface.get_next_method_execs()

                    if method_execs is None:
                        method_execs = []
                    
                    # Log HTN planning step with environment state and HTN knowledge base
                    task_exec_str = str(task_exec) if task_exec else "None"
                    method_execs_str = [str(me) for me in method_execs]
                    self.logger.log_event(
                        EventType.HTN_PLANNING_STEP,
                        {
                            "task_exec": task_exec_str,
                            "method_execs": method_execs_str,
                            "selected_method": None
                        },
                        self._get_env_state_dict(),
                        self._get_htn_knowledge_base_dict()
                    )
   

                    # If there are any MethodExs, wait for the user to assign them
                    #  with a reward label: 1, -1 (or not: None) and have the 
                    #  user_interface decide which method_exec will be applied

                    next_method_exec, rewards = \
                        self.user_interface.query_next_decomposition_and_rewards(
                            task_exec, method_execs)

                    # Log user decomposition selection with environment state and HTN knowledge base
                    task_exec_str = str(task_exec) if task_exec else "None"
                    method_execs_str = [str(me) for me in method_execs]
                    selected_index = method_execs.index(next_method_exec) if next_method_exec else None
                    self.logger.log_event(
                        EventType.USER_DECOMPOSITION_SELECTION,
                        {
                            "task_exec": task_exec_str,
                            "method_execs": method_execs_str,
                            "selected_index": selected_index,
                            "rewards": rewards
                        },
                        self._get_env_state_dict(),
                        self._get_htn_knowledge_base_dict()
                    )

                    # If there is no next_method_exec because:
                    #  1. Matching in the planner failed or 
                    #  2. The user decided to describe their own method
                    #  Then query the user to describe the grounded subtasks of the 
                    #  decomposition. This creates the next method execution.
                    if (next_method_exec is None):
                        next_method_exec = self.query_new_method_exec(task_exec)
                        print("Value next_method_exec.method.subtasks:", next_method_exec.method.subtasks)
                        print("type next_method_exec", type(next_method_exec))
                        self.user_interface.display_added_method(task_exec, next_method_exec)
                        rewards.append(1)
                        method_execs.append(next_method_exec)
                        
                    # Stage next_method_exec so that it is applied when 
                    #  planning continues in the next loop 
                    self.htn_interface.stage_method_exec(next_method_exec)

                    # Apply any rewards that were assigned 
                    for method_exec, reward in zip(method_execs, rewards):
                        method = method_exec.method
                        # method.cond_lrn.ifit(method_exec, 1)
                    

            except FailedPlanException:
                # Signify Failure
                self.logger.log_error("FailedPlanException", "HTN planning failed")
            except KeyboardInterrupt:
                # User interrupted the session
                self.logger.end_session()
                break
            except Exception as e:
                # Log any other errors
                import traceback
                self.logger.log_error("GeneralException", str(e), traceback.format_exc())
                raise

    def interpret(self, user_tasks: str) -> List[Task]:
        """
        Takes a string of natural language from the user and returns a list of Tasks
        """
        segmented_tasks = self.segment_gpt(user_tasks)
        
        # Log LLM segmentation with environment state and HTN knowledge base
        llm_response = self.gpt.get_chat_gpt_completion(f'{self.segment_prompt}"{user_tasks}"')
        self.logger.log_event(
            EventType.LLM_SEGMENTATION,
            {
                "user_tasks": user_tasks,
                "segmented_tasks": segmented_tasks,
                "llm_response": llm_response
            },
            self._get_env_state_dict(),
            self._get_htn_knowledge_base_dict()
        )
        
        while not self.user_interface.segment_confirmation(segmented_tasks):
            #not segment correctly
            # TODO consider adding/editing steps here.
            user_tasks = self.user_interface.ask_rephrase(user_tasks)
            segmented_tasks = self.segment_gpt(user_tasks)
            
            # Log user rephrase request with environment state and HTN knowledge base
            self.logger.log_event(
                EventType.USER_REPHRASE_REQUEST,
                {
                    "original_tasks": user_tasks,
                    "rephrased_tasks": user_tasks
                },
                self._get_env_state_dict(),
                self._get_htn_knowledge_base_dict()
            )

        for user_task in segmented_tasks:
            task_ungrounded = self.map_gpt(user_task)
            print("task_ungrounded", task_ungrounded)
            
            # Log LLM mapping with environment state and HTN knowledge base
            tasks = [t for t, _ in self.htn_interface.get_tasks()]
            descriptions = [desc for _, desc in self.htn_interface.get_tasks()]
            task_list = [f"[{chr(ord('a')+i)}] {task_to_gpt_str(task, descriptions[i])}"
                         for i, task in enumerate(tasks)]
            object_list = self.env.get_objects()
            name_list = [x.split('(')[0] for x in task_list]
            name_list.append(f"[{chr(ord('a')+len(task_list))}] None of the above; "
                             f'"{user_task}" would require a combination of actions.')
            task_str = ', '.join(task_list)
            object_str = ', '.join(object_list)
            name_str = '\n'.join(name_list)
            prompt = self.map_prompt % (task_str, object_str, user_task, name_str)
            llm_response = self.gpt.get_chat_gpt_completion(prompt)
            mapped_task_name = task_ungrounded.name if task_ungrounded else None
            self.logger.log_event(
                EventType.LLM_MAPPING,
                {
                    "user_task": user_task,
                    "mapped_task": mapped_task_name,
                    "llm_response": llm_response
                },
                self._get_env_state_dict(),
                self._get_htn_knowledge_base_dict()
            )
            
            # task ungrounded is None means the agent is not sure what the user means
            # can not map to a task in the domain
            # map_gpt: go to map to moveTo, map the action(predicate)
            
            if ((task_ungrounded is None and
                   not self.user_interface.map_new_method_confirmation(user_task)) or
                  (task_ungrounded is not None and
                   not self.user_interface.map_confirmation(user_task, task_ungrounded.name))):
                #correct the map result
                # TODO add to htn interface
                # TODO consider how we convert tasks to strings and handle args
                known_tasks = [t for t, _ in self.htn_interface.get_tasks()]
                # known_tasks = self.htn_interface.get_tasks()
                str_known_tasks = [task_to_gpt_str(task, "") for task in known_tasks]
                user_correction_index = self.user_interface.map_correction(user_task, str_known_tasks)
                
                # Log user map correction with environment state and HTN knowledge base
                self.logger.log_event(
                    EventType.USER_MAP_CORRECTION,
                    {
                        "user_task": user_task,
                        "available_tasks": str_known_tasks,
                        "selected_index": user_correction_index
                    },
                    self._get_env_state_dict(),
                    self._get_htn_knowledge_base_dict()
                )
                
                if user_correction_index is None:
                    task_ungrounded = None
                else:
                    task_ungrounded = known_tasks[int(user_correction_index)]

            if task_ungrounded is None:
                task_name = self.name_gpt(user_task)
                task_args = self.gen_gpt(user_task, task_name)
                
                # Log LLM task naming and generation with environment state and HTN knowledge base
                llm_name_response = self.gpt.get_chat_gpt_completion(f'{self.name_prompt}"{user_task}"')
                self.logger.log_event(
                    EventType.LLM_TASK_NAMING,
                    {
                        "user_task": user_task,
                        "task_name": task_name,
                        "llm_response": llm_name_response
                    },
                    self._get_env_state_dict(),
                    self._get_htn_knowledge_base_dict()
                )
                
                objects = self.env.get_objects()
                obj_str = ", ".join(objects)
                prompt = self.gen_prompt % (obj_str, user_task, task_name)
                llm_gen_response = self.gpt.get_chat_gpt_completion(prompt).strip()
                self.logger.log_event(
                    EventType.LLM_GENERATION,
                    {
                        "user_task": user_task,
                        "task_name": task_name,
                        "generated_args": task_args,
                        "llm_response": llm_gen_response
                    },
                    self._get_env_state_dict(),
                    self._get_htn_knowledge_base_dict()
                )
                
                if not self.user_interface.gen_confirmation(user_task, task_name, task_args):
                    # Log user gen confirmation with environment state and HTN knowledge base
                    self.logger.log_event(
                        EventType.USER_GEN_CONFIRMATION,
                        {
                            "user_task": user_task,
                            "task_name": task_name,
                            "task_args": task_args,
                            "confirmed": False
                        },
                        self._get_env_state_dict(),
                        self._get_htn_knowledge_base_dict()
                    )
                    
                    original_args = task_args.copy()
                    task_args = self.user_interface.gen_correction(task_name, task_args,
                                                           self.env.get_objects())
                    
                    self.logger.log_event(
                        EventType.USER_GEN_CORRECTION,
                        {
                            "task_name": task_name,
                            "original_args": original_args,
                            "corrected_args": task_args
                        },
                        self._get_env_state_dict(),
                        self._get_htn_knowledge_base_dict()
                    )
                else:
                    # Log user gen confirmation with environment state and HTN knowledge base
                    self.logger.log_event(
                        EventType.USER_GEN_CONFIRMATION,
                        {
                            "user_task": user_task,
                            "task_name": task_name,
                            "task_args": task_args,
                            "confirmed": True
                        },
                        self._get_env_state_dict(),
                        self._get_htn_knowledge_base_dict()
                    )
                
                yield Task(str(task_name), args=list(task_args))

            else:
            # ground task objects
                task_args = self.ground_gpt(user_task, task_ungrounded)
                
                num_args = len(task_ungrounded.args)
                object_list = self.env.get_objects()
                object_str = ', '.join(object_list)
                num_args_str = '%d argument%s' % (num_args, '' if num_args==1 else 's')
                num_objs_str = '%d object%s' % (num_args, '' if num_args==1 else 's')
                task_name = task_ungrounded.name
                o_list = ', '.join([('o%d' % (i+1)) for i in range(num_args)])
                prompt = self.ground_prompt % (task_to_gpt_str(task_ungrounded, ""), user_task, object_str, task_name, num_args_str, num_objs_str, task_name, o_list)
                llm_ground_response = self.gpt.get_chat_gpt_completion(prompt).strip()
                self.logger.log_event(
                    EventType.LLM_GROUNDING,
                    {
                        "user_task": user_task,
                        "task_name": task_ungrounded.name,
                        "grounded_args": task_args,
                        "llm_response": llm_ground_response
                    },
                    self._get_env_state_dict(),
                    self._get_htn_knowledge_base_dict()
                )
                
                # if pick the wrong object
                if not self.user_interface.ground_confirmation(task_ungrounded.name, task_args):
                    # Log user ground confirmation with environment state and HTN knowledge base
                    self.logger.log_event(
                        EventType.USER_GROUND_CONFIRMATION,
                        {
                            "task_name": task_ungrounded.name,
                            "task_args": task_args,
                            "confirmed": False
                        },
                        self._get_env_state_dict(),
                        self._get_htn_knowledge_base_dict()
                    )
                    
                    original_args = task_args.copy()
                    task_args = self.user_interface.ground_correction(task_ungrounded.name,
                                                                      task_args,
                                                                      self.env.get_objects())
                    
                    self.logger.log_event(
                        EventType.USER_GROUND_CORRECTION,
                        {
                            "task_name": task_ungrounded.name,
                            "original_args": original_args,
                            "corrected_args": task_args
                        },
                        self._get_env_state_dict(),
                        self._get_htn_knowledge_base_dict()
                    )
                else:
                    # Log user ground confirmation with environment state and HTN knowledge base
                    self.logger.log_event(
                        EventType.USER_GROUND_CONFIRMATION,
                        {
                            "task_name": task_ungrounded.name,
                            "task_args": task_args,
                            "confirmed": True
                        },
                        self._get_env_state_dict(),
                        self._get_htn_knowledge_base_dict()
                    )

                verbalized_task = self.verbalize_gpt(task_ungrounded, task_args)
                
                self.logger.log_event(
                    EventType.LLM_VERBALIZATION,
                    {
                        "task_name": task_ungrounded.name,
                        "task_args": task_args,
                        "verbalized_task": verbalized_task
                    },
                    self._get_env_state_dict(),
                    self._get_htn_knowledge_base_dict()
                )

                if (self.paraphrase_gpt(verbalized_task, user_task) or
                     self.user_interface.gen_confirmation(user_task, task_ungrounded.name, task_args)):
                    para_res = self.gpt.get_chat_gpt_completion(self.para_prompt % (user_task, verbalized_task))                    
                    self.logger.log_event(
                        EventType.LLM_PARAPHRASE_CHECK,
                        {
                            "verbalized_task": verbalized_task,
                            "user_task": user_task,
                            "is_paraphrase": para_res == 'yes'
                        },
                        self._get_env_state_dict(),
                        self._get_htn_knowledge_base_dict()
                    )
                    
                    yield Task(str(task_ungrounded.name), args=list(task_args))
                else:
                    for subtask in self.add_method_from_user_task(user_task):
                        yield subtask

    def query_new_method_exec(self, task_exec: TaskEx):
        """
        This is previous "add method" function. Returns an HTN method
        """
        state = self.env.get_state()
        task = task_exec.task 
        task_args = task_exec.match 
        verbalized_task = self.verbalize_gpt(task, task_args)
        user_subtasks = self.user_interface.ask_subtasks(verbalized_task)
        
        self.logger.log_event(
            EventType.USER_SUBTASK_DESCRIPTION,
            {
                "task_name": task.name,
                "user_subtasks": user_subtasks
            },
            self._get_env_state_dict(),
            self._get_htn_knowledge_base_dict()
        )
        
        subtasks = []
        for subtask in self.interpret(user_subtasks):
            subtasks.append(subtask)

        # TODO maybe consider a gpt module that names these better...
        arg_map = {arg: V(chr(ord('A')+i))
                   for i, arg in enumerate(task_args)}

        task_args_v = [arg_map[arg] for arg in task_args]

        subtasks_v = []
        subtask_execs = []
        for subtask in subtasks:
            v_args = [arg_map[subarg] if subarg in arg_map else subarg
                        for subarg in subtask.args]
            print("v_args", v_args)
            subtask_v = Task(subtask.name, args=v_args)
            subtask_exec = TaskEx(subtask_v, state, match=subtask.args)
            subtasks_v.append(subtask_v)
            subtask_execs.append(subtask_exec)

        print("task_args_v", task_args_v)
        method = Method(task.name, args=task_args_v, subtasks=subtasks_v)
        method_exec = MethodEx(method, state,
            match=task_args,
            parent_task_exec=task_exec,
            subtask_execs=subtask_execs
        )
        for subtask_exec in subtask_execs:
            subtask_exec.parent_exec = method_exec

        self.htn_interface.add_method_exec(method_exec)
        
        method_name = method.name
        method_args = [str(arg) for arg in method.args]
        subtask_names = [subtask.name for subtask in method.subtasks]
        self.logger.log_event(
            EventType.HTN_METHOD_ADDITION,
            {
                "method_name": method_name,
                "method_args": method_args,
                "subtasks": subtask_names
            },
            self._get_env_state_dict(),
            self._get_htn_knowledge_base_dict()
        )
        
        return method_exec

    def segment_gpt(self, user_tasks: str) -> List[str]:
        # SEGMENTS: 1. "cook an onion" (resolved pronouns: "cook an onion")
        resp = self.gpt.get_chat_gpt_completion(f'{self.segment_prompt}"{user_tasks}"')
        segmented_user_tasks = []
        for line in resp.split('\n'):
            # Code parses string '2. "interact with it" (resolved pronouns: "interact with the onion")'
            # to get "interact with the onion" out.
            segmented_user_tasks.append(line.split('"')[3])

        return segmented_user_tasks

    def name_gpt(self, user_task: str) -> str:
        """
        Takes user task string and returns a task name that matches it.
        """
        resp = self.gpt.get_chat_gpt_completion(f'{self.name_prompt}"{user_task}"')
        return resp.split('(')[0]

    def map_gpt(self, user_task: str) -> Optional[Task]:
        """
        Takes user input and htn_methods and maps to a method.

        Might return... Task("moveTo", V("X"))
        """

        # TODO get_tasks returns -> [Task('moveTo', 'V(X)'), ...]
        tasks = [t for t, _ in self.htn_interface.get_tasks()]
        descriptions = [desc for _, desc in self.htn_interface.get_tasks()]

        task_list = [f"[{chr(ord('a')+i)}] {task_to_gpt_str(task, descriptions[i])}"
                     for i, task in enumerate(tasks)]

        # TODO get_objects returns -> ['onion', 'pot', ...]
        object_list = self.env.get_objects()
        name_list = [x.split('(')[0] for x in task_list]
        name_list.append(f"[{chr(ord('a')+len(task_list))}] None of the above; "
                         f'"{user_task}" would require a combination of actions.')

        task_str = ', '.join(task_list)
        object_str = ', '.join(object_list)
        name_str = '\n'.join(name_list)

        prompt = self.map_prompt % (task_str, object_str, user_task, name_str)
        resp = self.gpt.get_chat_gpt_completion(prompt)

        choice = None
        for i in range(len(resp)):
            if resp[i] == '[':
                choice = resp[i+1]
                break
        choice = ord(choice)-ord('a')

        chosen_task = None
        if choice < len(task_list):
            chosen_task = tasks[choice]

        return chosen_task

    def ground_gpt(self, user_task: str, task_ungrounded: Task) -> List[str]:
        """
        Takes the user task,
        the name from map
        the kb
        the objects in environment

        returns list of argument mappings for task name
        """
        num_args = len(task_ungrounded.args)
        if num_args == 0:
            return task_ungrounded.args

        object_list = self.env.get_objects()
        object_str = ', '.join(object_list)

        num_args_str = '%d argument%s' % (num_args, '' if num_args==1 else 's')
        num_objs_str = '%d object%s' % (num_args, '' if num_args==1 else 's')

        task_name = task_ungrounded.name

        o_list = ', '.join([('o%d' % (i+1)) for i in range(num_args)])

        prompt = self.ground_prompt % (task_to_gpt_str(task_ungrounded, ""), user_task, object_str, task_name, num_args_str, num_objs_str, task_name, o_list)

        resp = self.gpt.get_chat_gpt_completion(prompt).strip()

        if '"' in resp:
            resp = resp.replace('"', '').strip()
        
        resp = resp.replace(" ", "")
        resp = resp.split("(")[1]
        resp = resp.split(")")[0]
        resp = resp.split(",")

        return resp

    def gen_gpt(self, user_task: str, task_name: str) -> List[str]:

        # objects = set(arg for task in subtasks for arg in task.args)
        objects = self.env.get_objects()

        obj_str = ", ".join(objects)
        prompt = self.gen_prompt % (obj_str, user_task, task_name)
        resp = self.gpt.get_chat_gpt_completion(prompt).strip()

        if ': ' in resp:
            resp = resp.split(': ')[1]

        if '(' not in resp:
            return resp + '()'
        
        resp = resp.replace(" ", "")
        resp = resp.split("(")[1]
        resp = resp.split(")")[0]
        resp = resp.split(",")
        return resp

    def verbalize_gpt(self, task_ungrounded: Task, task_args: List[str]) -> str:
        """
        Takes the task_ungrounded and its args and converts it into an English
        formatted verbalization that can be compared with the user_task.
        """
        task = f"{task_ungrounded.name}({', '.join(task_args)})"
        return self.gpt.get_chat_gpt_completion(f"{self.verb_prompt}{task}")

    def paraphrase_gpt(self, verbalized_task: str, user_task: str) -> bool:
        """
        Takes a verbalized task (generated from task name and args) and the
        original user_task and returns whether they are the same.
        """
        res = self.gpt.get_chat_gpt_completion(
                self.para_prompt % (user_task, verbalized_task))
        return res == 'yes'

    def confirm_task_decomposition(self, task: Task, subtasks: List[Task]) -> bool:
        # convert task and subtasks into english using GPT prompt.
        # use user interface to confirm with user
        # return bool based on confirmation
        verbalized_task = self.verbalize_gpt(task, task.args)
        verbalized_subtasks = [self.verbalize_gpt(subtask, subtask.args) for subtask in subtasks]
        return self.user_interface.confirm_task_decomposition(verbalized_task, verbalized_subtasks)

    def confirm_task_execution(self, task: Task) -> bool:
        # convert task into english using GPT prompt.
        # use user interface to confirm with user
        # return bool based on confirmation
        verbalized_task = self.verbalize_gpt(task, task.args)
        return self.user_interface.confirm_task_execution(verbalized_task)
    
    def _get_env_state_dict(self) -> Dict[str, Any]:
        """
        Get environment state as a dictionary for logging
        """
        try:
            state = self.env.get_state()
            if state is None:
                return {}
            
            if isinstance(state, list):
                serializable_state = []
                for item in state:
                    try:
                        serializable_state.append(str(item))
                    except Exception:
                        serializable_state.append(f"<non-serializable: {type(item).__name__}>")
                return {"state": serializable_state}
            
            elif isinstance(state, dict):
                serializable_state = {}
                for key, value in state.items():
                    try:
                        serializable_state[str(key)] = str(value)
                    except Exception:
                        serializable_state[str(key)] = f"<non-serializable: {type(value).__name__}>"
                return {"state": serializable_state}
            
            else:
                return {"state": str(state)}
                
        except Exception as e:
            return {"error": str(e)}
    
    def _get_htn_knowledge_base_dict(self) -> Dict[str, Any]:
        """Get HTN knowledge base as a dictionary for logging"""
        try:
            tasks = [t for t, _ in self.htn_interface.get_tasks()]
            return {
                "tasks": [{"name": task.name, "args": [str(arg) for arg in task.args]} for task in tasks]
            }
        except Exception as e:
            return {"error": str(e)}


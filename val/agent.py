import json

from typing import List
from typing import Optional
from typing import Union

from val.utils import load_prompt
from val.utils import display_grounding_args
from val.utils import get_display_objects
from val.utils import normalize_grounding_args
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


class ValAgent:

    def __init__(self,
                 env: AbstractEnvInterface,
                 user_interface_class,
                 htn_interface_class,
                 openai_key: Union[str, dict]):

        self.segment_prompt = load_prompt("prompts/chat_segmenter.txt")
        self.grounding_prompt = load_prompt("prompts/unified_grounding.txt")
        
        self.name_prompt = load_prompt('prompts/chat_namer.txt')
        self.gen_prompt = load_prompt('prompts/chat_gen.txt')
        self.para_prompt = load_prompt('prompts/chat_paraphrase_ider.txt')
        self.verb_prompt = load_prompt('prompts/chat_verbalizer.txt')
        self.map_prompt = load_prompt('prompts/chat_map.txt')
        self.ground_prompt = load_prompt('prompts/chat_ground.txt')
        self.explanation_prompt = load_prompt('prompts/explain_decision.txt')

        self.gpt = GPTCompleter(openai_key)

        self.user_interface = user_interface_class()
        self.env = env
        self.htn_interface = htn_interface_class(self, self.env)
        self.method_rewards = {}

    def _stable_json_key(self, value):
        return json.dumps(value, sort_keys=True, default=str)

    def _condition_key(self, task_exec: TaskEx):
        task_dict = task_exec.as_dict()
        return self._stable_json_key({
            "task_name": task_dict.get("name"),
        })

    def _method_reward_key(self, method_exec: MethodEx):
        method = method_exec.method
        return self._stable_json_key({
            "method_name": method.name,
            "method_args": list(getattr(method, "args", [])),
            "preconditions": [str(precondition) for precondition in (getattr(method, "preconditions", None) or [])],
            "children": [
                {
                    "name": subtask.name,
                    "args": list(getattr(subtask, "args", [])),
                }
                for subtask in getattr(method, "subtasks", [])
            ],
        })

    def _method_reward(self, task_exec: TaskEx, method_exec: MethodEx):
        return self.method_rewards.get(self._condition_key(task_exec), {}).get(
            self._method_reward_key(method_exec),
            0.0,
        )

    def _rank_method_execs(self, task_exec: TaskEx, method_execs: List[MethodEx]):
        return sorted(
            method_execs,
            key=lambda method_exec: -self._method_reward(task_exec, method_exec),
        )

    def _apply_method_reward(self, task_exec: TaskEx, method_exec: MethodEx, reward):
        if reward is None or reward == 0:
            return

        condition_key = self._condition_key(task_exec)
        method_key = self._method_reward_key(method_exec)
        rewards_for_condition = self.method_rewards.setdefault(condition_key, {})
        rewards_for_condition[method_key] = (
            rewards_for_condition.get(method_key, 0.0) + reward
        )

    def start(self):
        while True:

            # Get current task node from planner and pass this to the user interface
            tasks = [self.verbalize_gpt(t, [arg.name for arg in t.args])
                                        for t, _ in self.htn_interface.get_tasks()]
            self.user_interface.display_known_tasks(tasks)

            user_tasks = self.user_interface.request_user_task()
            tasks = [task for task in self.interpret(user_tasks)]
            
            # Filter out any special string responses
            actual_tasks = [task for task in tasks if not isinstance(task, str)]
            
            # If no actual tasks, return
            if not actual_tasks:
                return
            
            print(f"Tasks: {actual_tasks}")
            self.htn_interface.add_tasks(actual_tasks)
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
                        self.user_interface.finish_task()
                        break

                    # Get the method executions considered by the planner
                    task_exec, method_execs = self.htn_interface.get_next_method_execs()
                    
                    print(f"DEBUG: task_exec = {task_exec}")
                    print(f"DEBUG: method_execs = {method_execs}")
                    print(f"DEBUG: method_execs type = {type(method_execs)}")
                    if method_execs:
                        print(f"DEBUG: method_execs length = {len(method_execs)}")

                    
                    # if this is an unknown task, the user interface will return next_method_exec as None
                    # and it will go to query_new_method_exec
                    if method_execs is None:
                        method_execs = []
                        print("DEBUG: method_execs was None, set to empty list")
                    elif method_execs:
                        method_execs = self._rank_method_execs(task_exec, method_execs)
   

                    # If there are any MethodExs, wait for the user to assign them
                    #  with a reward label: 1, -1 (or not: None) and have the 
                    #  user_interface decide which method_exec will be applied
                    available_actions = [task.name for task, _ in self.htn_interface.get_tasks()]

                    # Query decomposition with edit options (this will display the tree and wait for response)
                    decision_explanation = None
                    if method_execs:
                        decision_explanation = self.explain_decision(task_exec, method_execs, method_execs[0])

                    user_choice, next_method_exec, rewards = \
                        self.user_interface.query_next_decomposition_with_edit(
                            task_exec, method_execs, available_actions,
                            get_display_objects(self.env.get_objects()),
                            decision_explanation)
                        
                    # Handle user choice
                    if user_choice == 'approve':
                        print("user_choice", user_choice)
                        # Display the approved decomposition tree
                        self.user_interface.display_added_method(task_exec, next_method_exec)

                    #### edit from gui ####
                    elif user_choice == 'gui_edit':
                        edited_decomposition = self.user_interface.last_edited_decomposition
                        next_method_exec = self.edit_from_gui(
                                task_exec, edited_decomposition
                            )
                        self.user_interface.display_added_method(task_exec, next_method_exec)
                        rewards = list(rewards)
                        if len(rewards) < len(method_execs):
                            rewards.extend([None] * (len(method_execs) - len(rewards)))
                        rewards.append(1)  # Give positive reward to the new method
                        method_execs.append(next_method_exec)
                        print("showed the added method")
                        
                    #### add new method ####    
                    # If there is no next_method_exec because:
                    #  1. Matching in the planner failed or 
                    #  2. The user decided to describe their own method
                    #  Then query the user to describe the grounded subtasks of the 
                    #  decomposition. This creates the next method execution.
                    elif user_choice == 'add_method':
                        next_method_exec = self.query_new_method_exec(task_exec)
                        print("Value next_method_exec.method.subtasks:", next_method_exec.method.subtasks)
                        print("type next_method_exec", type(next_method_exec))
                        self.user_interface.display_added_method(task_exec, next_method_exec)
                        rewards = list(rewards)
                        if len(rewards) < len(method_execs):
                            rewards.extend([None] * (len(method_execs) - len(rewards)))
                        rewards.append(1)
                        method_execs.append(next_method_exec)
                      
                    # Stage next_method_exec so that it is applied when 
                    #  planning continues in the next loop 
                    self.htn_interface.stage_method_exec(next_method_exec)

                    # Apply any rewards that were assigned 
                    for method_exec, reward in zip(method_execs, rewards):
                        self._apply_method_reward(task_exec, method_exec, reward)
                    

            except FailedPlanException:
                # Signify Failure
                pass

    def interpret(self, user_tasks: str) -> List[Task]:
        """
        Takes a string of natural language from the user and returns a list of Tasks
        Simplified version without excessive confirmations
        """
        segmented_tasks = self.segment_gpt(user_tasks)
        
        # Allow correction of segmentation
        while not self.user_interface.segment_confirmation(segmented_tasks):
            user_tasks = self.user_interface.ask_rephrase(user_tasks)
            segmented_tasks = self.segment_gpt(user_tasks)

        for user_task in segmented_tasks:
            # Use unified grounding to extract action and objects
            task_name, task_args = self.unified_grounding_gpt(user_task)
            
            # Allow correction of the grounded result
            # Get available actions from htn_interface
            available_actions = [task.name for task, _ in self.htn_interface.get_tasks()]
            
            # Correct grounding - this will show the grounding correction interface
            display_task_args = display_grounding_args(task_name, task_args)
            corrected_task_name, corrected_task_args = self.user_interface.correct_grounding(
                user_task, task_name, display_task_args, get_display_objects(self.env.get_objects()), available_actions
            )
            
            # Create task and yield it
            # Note: We don't show thinking analysis here because it will be shown
            # together with decomposition tree in the main loop
            yield Task(str(corrected_task_name), args=list(corrected_task_args))
            
            
    def query_new_method_exec(self, task_exec: TaskEx):
        """
        This is previous "add method" function. Returns an HTN method
        """
        state = self.env.get_state()
        task = task_exec.task 
        task_args = tuple(task_exec.match or task.args)
        verbalized_task = self.verbalize_gpt(task, task_args)
        user_subtasks = self.user_interface.ask_subtasks(verbalized_task, task_exec=task_exec)
        subtasks = []
        for subtask in self.interpret(user_subtasks):
            subtasks.append(subtask)

        # Use the generic method to create MethodEx (no preconditions for manual input)
        return self.create_method_exec(task_exec, subtasks)
    
    
####### edit functions: from gui #######
#edit functions are used to create a new method execution

    def edit_from_gui(self, task_exec: TaskEx, edited_decomposition: dict) -> MethodEx:
        """
        Create a new MethodEx from user-edited decomposition
        Args:
            task_exec: The task being decomposed
            edited_decomposition: Dictionary containing the edited decomposition from frontend
        Returns:
            MethodEx: The new method execution created from the edited decomposition
        """
        # Extract subtasks from edited decomposition
        subtasks = []
        for subtask_group in edited_decomposition['subtasks']:
            for subtask_data in subtask_group:
                task_name = subtask_data['task_name']
                task_args_list = subtask_data['args']
                task_args_list = normalize_grounding_args(task_name, task_args_list)
                subtask = Task(task_name, args=task_args_list)
                subtasks.append(subtask)

        # Extract preconditions if provided
        preconditions = []
        if 'preconditions' in edited_decomposition and edited_decomposition['preconditions']:
            for precondition_name in edited_decomposition['preconditions']:
                # Create simple preconditions - you might want to parse more complex ones
                precondition = Fact(precondition_name, "=", True)
                preconditions.append(precondition)
        
        # Use the generic method to create MethodEx with preconditions
        return self.create_method_exec(task_exec, subtasks, preconditions)
    
    def create_method_exec(self, task_exec: TaskEx, subtasks: List[Task], preconditions: List[Fact] = None) -> MethodEx:
        """
        Generic method to create a MethodEx from subtasks and preconditions
        Args:
            task_exec: The task being decomposed
            subtasks: List of subtasks
            preconditions: List of preconditions (optional)
        Returns:
            MethodEx: The new method execution
        """
        state = self.env.get_state()
        task = task_exec.task 
        task_args = task_exec.match 
        
        # Use empty list if no preconditions provided
        if preconditions is None:
            preconditions = []
        
        # Create argument mapping
        arg_map = {arg: V(chr(ord('A')+i))
                   for i, arg in enumerate(task_args)}

        task_args_v = tuple(arg_map[arg] for arg in task_args)

        # Create subtasks with variables
        subtasks_v = []
        subtask_execs = []
        for subtask in subtasks:
            subtask_args = tuple(subtask.args)
            v_args = tuple(arg_map[subarg] if subarg in arg_map else subarg
                        for subarg in subtask_args)
            print("v_args", v_args)
            subtask_v = Task(subtask.name, args=v_args)
            subtask_exec = TaskEx(subtask_v, state, match=subtask_args)
            subtasks_v.append(subtask_v)
            subtask_execs.append(subtask_exec)

        print("task_args_v", task_args_v)
        method = Method(task.name, args=task_args_v, subtasks=subtasks_v, preconditions=preconditions)
        method_exec = MethodEx(method, state,
            match=task_args,
            parent_task_exec=task_exec,
            subtask_execs=subtask_execs
        )
        for subtask_exec in subtask_execs:
            subtask_exec.parent_exec = method_exec

        self.htn_interface.add_method_exec(method_exec)
        return method_exec

    


    def explain_decision(self, task_exec: TaskEx, method_execs: list, chosen_method_exec: MethodEx) -> str:
        """
        Generate an explanation for why a specific method was chosen for task decomposition.
        """
        # Parameter validation
        if task_exec is None:
            print("WARNING: task_exec is None")
            return "Cannot explain decision: task_exec is None"
        
        if method_execs is None or len(method_execs) == 0:
            print("WARNING: method_execs is None or empty")
            return "Cannot explain decision: no available methods"
        
        if chosen_method_exec is None:
            print("WARNING: chosen_method_exec is None")
            return "Cannot explain decision: no method was chosen"
        
        print(f"DEBUG: Explaining decision for task: {task_exec}")
        print(f"DEBUG: Number of available methods: {len(method_execs)}")
        print(f"DEBUG: Chosen method: {chosen_method_exec}")
        
        # Get current state information
        current_state = self.env.get_state()
        print(f"DEBUG: Current state has {len(current_state)} items")
        
        # Format task information
        try:
            task_str = f"{task_exec.task.name}({', '.join([str(arg) for arg in task_exec.match])})"
            print(f"DEBUG: Task string: {task_str}")
        except Exception as e:
            print(f"ERROR formatting task: {e}")
            task_str = f"{task_exec.task.name if task_exec.task else 'unknown'}"
        
        # Format available methods
        method_strs = []
        precondition_strs = []
        try:
            for i, method_exec in enumerate(method_execs):
                if method_exec is None or method_exec.method is None:
                    method_strs.append(f"Method {i+1}: [INVALID_METHOD]")
                    precondition_strs.append(f"Method {i+1}: [INVALID_METHOD]")
                    continue
                    
                subtasks = []
                for subtask in method_exec.method.subtasks:
                    if subtask is None:
                        subtasks.append("INVALID_SUBTASK")
                    else:
                        subtask_str = f"{subtask.name}({', '.join([str(arg) for arg in subtask.args])})"
                        subtasks.append(subtask_str)
                method_strs.append(f"Method {i+1}: [{', '.join(subtasks)}]")

                preconditions = getattr(method_exec.method, "preconditions", None) or []
                precondition_str = ", ".join(str(precondition) for precondition in preconditions)
                precondition_strs.append(f"Method {i+1}: [{precondition_str or 'none'}]")
            available_methods_str = "; ".join(method_strs)
            method_preconditions_str = "; ".join(precondition_strs)
            print(f"DEBUG: Available methods: {available_methods_str}")
            print(f"DEBUG: Method preconditions: {method_preconditions_str}")
        except Exception as e:
            print(f"ERROR formatting methods: {e}")
            available_methods_str = "Error formatting methods"
            method_preconditions_str = "Error formatting preconditions"
        
        # Format chosen method
        try:
            if chosen_method_exec.method is None:
                chosen_method_str = "[INVALID_CHOSEN_METHOD]"
            else:
                chosen_subtasks = []
                for subtask in chosen_method_exec.method.subtasks:
                    if subtask is None:
                        chosen_subtasks.append("INVALID_SUBTASK")
                    else:
                        subtask_str = f"{subtask.name}({', '.join([str(arg) for arg in subtask.args])})"
                        chosen_subtasks.append(subtask_str)
                chosen_method_str = f"[{', '.join(chosen_subtasks)}]"
            print(f"DEBUG: Chosen method: {chosen_method_str}")
        except Exception as e:
            print(f"ERROR formatting chosen method: {e}")
            chosen_method_str = "[ERROR_FORMATTING_CHOSEN_METHOD]"
        
        # Format state information (simplified for readability)
        state_info = []
        try:
            for item in current_state:
                if isinstance(item, dict):
                    if 'object' in item:
                        state_info.append(f"{item['object']}: {item.get('status', 'present')}")
                    elif 'terrain' in item:
                        state_info.append(f"terrain at ({item['x']},{item['y']}): {item['terrain']}")
            current_state_str = "; ".join(state_info[:10])  # Limit to first 10 items for readability
            print(f"DEBUG: State string: {current_state_str}")
        except Exception as e:
            print(f"ERROR formatting state: {e}")
            current_state_str = "Error formatting state"
        
        # Generate explanation using GPT
        try:
            prompt = self.explanation_prompt % (
                task_str,
                available_methods_str,
                method_preconditions_str,
                current_state_str,
                chosen_method_str
            )
            print(f"DEBUG: Generated prompt length: {len(prompt)}")
        
            
            explanation = self.gpt.get_chat_gpt_completion(prompt)
            print(f"DEBUG: Generated explanation length: {len(explanation)}")
            explanation = explanation.removeprefix("Explanation:").strip()
            return explanation
        except Exception as e:
            print(f"ERROR generating explanation: {e}")
            return f"Error generating explanation: {e}"


####### unified old grounding functions into one function #######
    def segment_gpt(self, user_tasks: str) -> List[str]:
        # SEGMENTS: 1. "cook an onion" (resolved pronouns: "cook an onion")
        resp = self.gpt.get_chat_gpt_completion(f'{self.segment_prompt}"{user_tasks}"')
        segmented_user_tasks = []
        for line in resp.split('\n'):
            # Code parses string '2. "interact with it" (resolved pronouns: "interact with the onion")'
            # to get "interact with the onion" out.
            segmented_user_tasks.append(line.split('"')[3])

        return segmented_user_tasks


    def unified_grounding_gpt(self, user_task: str) -> tuple[str, List[str]]:
        """
        Unified method to extract action and objects from natural language
        Returns (task_name, task_args)
        """
        # Get available tasks and objects
        known_tasks = [t for t, _ in self.htn_interface.get_tasks()]
        task_descriptions = [desc for _, desc in self.htn_interface.get_tasks()]
        objects = get_display_objects(self.env.get_objects())
        
        # Create task list for prompt
        task_list = [f"[{chr(ord('a')+i)}] {task_to_gpt_str(task, task_descriptions[i])}"
                     for i, task in enumerate(known_tasks)]
        available_actions = ', '.join(task_list)
        available_objects = ', '.join(objects)
        
        # Load and format prompt
        
        prompt = self.grounding_prompt.format(
            available_actions=available_actions,
            available_objects=available_objects,
            user_input=user_task
        )
        
        resp = self.gpt.get_chat_gpt_completion(prompt).strip()
        
        # Parse response
        lines = resp.split('\n')
        task_name = "unknown"
        task_args = []
        
        for line in lines:
            if line.startswith('ACTION:'):
                task_name = line.split('ACTION:')[1].strip()
            elif line.startswith('OBJECTS:'):
                objects_str = line.split('OBJECTS:')[1].strip()
                if objects_str:
                    task_args = [obj.strip() for obj in objects_str.split(',')]
        
        return task_name, normalize_grounding_args(task_name, task_args)

    def verbalize_gpt(self, task_ungrounded: Task, task_args: List[str]) -> str:
        """
        Takes the task_ungrounded and its args and converts it into an English
        formatted verbalization that can be compared with the user_task.
        """
        task = f"{task_ungrounded.name}({', '.join(task_args)})"
        prompt = f"{self.verb_prompt.rstrip()}\n{task}\n***\n"
        return self.gpt.get_chat_gpt_completion(prompt).strip()

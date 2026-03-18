from typing import List
from typing import Optional
from typing import Union

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

import re


class ValAgent:

    def __init__(self,
                 env: AbstractEnvInterface,
                 user_interface_class,
                 htn_interface_class,
                 openai_key: Union[str, dict]):

        self.segment_prompt = load_prompt("prompts/chat_segmenter.txt")
        self.grounding_prompt = load_prompt("prompts/unified_grounding.txt")
        self.precondition_parser_prompt = load_prompt("prompts/precondition_parser.txt")
        
        self.name_prompt = load_prompt('prompts/chat_namer.txt')
        self.gen_prompt = load_prompt('prompts/chat_gen.txt')
        self.para_prompt = load_prompt('prompts/chat_paraphrase_ider.txt')
        self.verb_prompt = load_prompt('prompts/chat_verbalizer.txt')
        self.map_prompt = load_prompt('prompts/chat_map.txt')
        self.ground_prompt = load_prompt('prompts/chat_ground.txt')
        self.explanation_prompt = load_prompt('prompts/newprompts/1st try.txt')

        self.gpt = GPTCompleter(openai_key)

        self.user_interface = user_interface_class()
        self.env = env
        self.htn_interface = htn_interface_class(self, self.env)

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
   

                    # If there are any MethodExs, wait for the user to assign them
                    #  with a reward label: 1, -1 (or not: None) and have the 
                    #  user_interface decide which method_exec will be applied
                    available_actions = [task.name for task, _ in self.htn_interface.get_tasks()]

                    # Query decomposition with edit options (this will display the tree and wait for response)
                    user_choice, next_method_exec, rewards = \
                        self.user_interface.query_next_decomposition_with_edit(
                            task_exec, method_execs, available_actions, self.env.get_objects())
                        
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
                        rewards.append(1)  # Give positive reward to the new method
                        method_execs.append(next_method_exec)
                        print("showed the added method")
                        
                    #### edit from chatbot ####
                    elif user_choice == 'chatbot_edit':
                        chatbot_response = self.user_interface.chatbot_response
                        preconditions = self.user_interface.last_preconditions
                        next_method_exec = self.edit_from_chat(
                                task_exec, chatbot_response, preconditions
                            )
                        rewards.append(1)  # Give positive reward to the new method
                        method_execs.append(next_method_exec)
                        
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
            corrected_task_name, corrected_task_args = self.user_interface.correct_grounding(
                user_task, task_name, task_args, self.env.get_objects(), available_actions
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
        task_args = task_exec.match 
        verbalized_task = self.verbalize_gpt(task, task_args)
        user_subtasks = self.user_interface.ask_subtasks(verbalized_task)
        subtasks = []
        for subtask in self.interpret(user_subtasks):
            subtasks.append(subtask)

        # Use the generic method to create MethodEx (no preconditions for manual input)
        return self.create_method_exec(task_exec, subtasks)
    
    def display_thinking_analysis_after_grounding(self, user_task: str, task_name: str, task_args: List[str]):
        """
        Display thinking analysis after grounding to show the user what was understood
        """
        # Get environment objects for context
        env_objects = self.env.get_objects()
        objects_text = ', '.join(env_objects[:5])  # Show first 5 objects
        if len(env_objects) > 5:
            objects_text += f" and {len(env_objects) - 5} more..."
        
        # Create thinking-style analysis text
        task_args_text = ', '.join(task_args) if task_args else 'no objects'
        analysis_text = f"""Thinking...

The game environment contains {objects_text}.

Based on your input "{user_task}", I understood this as the action: {task_name}({task_args_text}).

Is it correct?"""
        
        # Display the thinking analysis in chatbot
        self.user_interface.display_thinking_analysis(
            user_task, task_name, task_args, analysis_text
        )

    def display_thinking_analysis_and_decomposition_tree(self, user_task: str, task_name: str, task_args: List[str], task_exec: TaskEx, method_execs: List[MethodEx]):
        """
        Display thinking analysis and decomposition tree after grounding
        """
        # Get environment objects for context
        env_objects = self.env.get_objects()
        objects_text = ', '.join(env_objects[:5])  # Show first 5 objects
        if len(env_objects) > 5:
            objects_text += f" and {len(env_objects) - 5} more..."
        
        # Create thinking-style analysis text
        task_args_text = ', '.join(task_args) if task_args else 'no objects'
        analysis_text = f"""Thinking...

The game environment contains {objects_text}.

Based on your input "{user_task}", I understood this as the action: {task_name}({task_args_text}).

Is it correct?"""
        
        # Display the thinking analysis in chatbot
        self.user_interface.display_thinking_analysis(
            user_task, task_name, task_args, analysis_text
        )
        
        # Display decomposition tree if methods are available
        if method_execs and len(method_execs) > 0:
            available_actions = [task.name for task, _ in self.htn_interface.get_tasks()]
            self.user_interface.query_next_decomposition_with_edit(
                task_exec, method_execs, available_actions, env_objects
            )
    
####### edit functions: from chatbot and gui #######
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
    
    
    def edit_from_chat(self, task_exec: TaskEx, chatbot_response: str, preconditions: List[str]) -> MethodEx:
        """
        Create a new MethodEx from chatbot response
        Args:
            task_exec: The task being decomposed
            chatbot_response: String response from chatbot describing the decomposition
            preconditions: List of precondition strings (legacy parameter, not used)
        Returns:
            MethodEx: The new method execution created from the chatbot response
        """
        task_name = task_exec.task.name
        
        # Parse preconditions
        parsed_preconditions = self.parse_preconditions(chatbot_response, task_name)
        precondition_names = [str(p) for p in parsed_preconditions]
        
        # Parse subtasks from chatbot response
        subtasks = []
        for subtask in self.interpret(chatbot_response):
            subtasks.append(subtask)
        
        subtask_names = [f"{s.name}({', '.join(s.args)})" for s in subtasks]
        
        # Display comprehensive decomposition analysis
        self.user_interface.display_decomposition_analysis(task_name, chatbot_response, subtask_names, precondition_names)
        
        # Display method creation process
        self.user_interface.display_method_creation(task_name, subtask_names, precondition_names)

        # Use the generic method to create MethodEx with preconditions
        return self.create_method_exec(task_exec, subtasks, parsed_preconditions)



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

        task_args_v = [arg_map[arg] for arg in task_args]

        # Create subtasks with variables
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

    def parse_preconditions(self, chatbot_response: str, task_name: str) -> List[Fact]:
        """
        Hybrid approach to parse preconditions from chatbot response:
        1. Use NLP/rule-based parsing for common patterns
        2. Fall back to LLM for complex cases
        Args:
            chatbot_response: The chatbot response describing the decomposition
            task_name: The name of the task being decomposed
        Returns:
            List[Fact]: List of parsed Fact objects
        """
        # First try rule-based parsing for common precondition patterns
        parsed_preconditions = self._rule_based_precondition_parsing(chatbot_response, task_name)
        
        # If rule-based parsing found preconditions, return them
        if parsed_preconditions:
            print(f"Rule-based parsing found {len(parsed_preconditions)} preconditions")
            return parsed_preconditions
        
        # Fall back to LLM parsing for complex cases
        print("Rule-based parsing found no preconditions, falling back to LLM")
        return self._llm_based_precondition_parsing(chatbot_response, task_name)
    
    def _rule_based_precondition_parsing(self, chatbot_response: str, task_name: str) -> List[Fact]:
        """
        Rule-based parsing for common precondition patterns
        """
        preconditions = []
        response_lower = chatbot_response.lower()
        
        # Common precondition patterns
        patterns = [
            # Resource availability
            (r'need\s+(\w+)\s*[>=]\s*(\d+)', 'resource_check', '>='),
            (r'require\s+(\w+)\s*[>=]\s*(\d+)', 'resource_check', '>='),
            (r'at\s+least\s+(\d+)\s+(\w+)', 'resource_check', '>='),
            (r'more\s+than\s+(\d+)\s+(\w+)', 'resource_check', '>'),
            
            # State conditions
            (r'(\w+)\s+must\s+be\s+(\w+)', 'state_check', '='),
            (r'(\w+)\s+should\s+be\s+(\w+)', 'state_check', '='),
            (r'(\w+)\s+is\s+(\w+)', 'state_check', '='),
            
            # Boolean conditions
            (r'(\w+)\s+available', 'availability', '='),
            (r'(\w+)\s+ready', 'readiness', '='),
            (r'(\w+)\s+empty', 'emptiness', '='),
        ]
        
        for pattern, fact_type, operator in patterns:
            matches = re.findall(pattern, response_lower)
            for match in matches:
                if fact_type == 'resource_check':
                    if len(match) == 2:
                        value, resource = match
                        try:
                            value = int(value)
                            fact_name = f"{resource}_count"
                            preconditions.append(Fact(fact_name, operator, value))
                        except ValueError:
                            continue
                elif fact_type == 'state_check':
                    if len(match) == 2:
                        object_name, state = match
                        fact_name = f"{object_name}_state"
                        preconditions.append(Fact(fact_name, operator, state))
                elif fact_type in ['availability', 'readiness', 'emptiness']:
                    if len(match) == 1:
                        object_name = match[0]
                        fact_name = f"{object_name}_{fact_type}"
                        preconditions.append(Fact(fact_name, operator, True))
        
        # Special case: check for negation patterns
        neg_patterns = [
            (r'no\s+(\w+)', 'resource_check', '='),
            (r'(\w+)\s+not\s+(\w+)', 'state_check', '!='),
        ]
        
        for pattern, fact_type, operator in neg_patterns:
            matches = re.findall(pattern, response_lower)
            for match in matches:
                if fact_type == 'resource_check':
                    if len(match) == 1:
                        resource = match[0]
                        fact_name = f"{resource}_count"
                        preconditions.append(Fact(fact_name, operator, 0))
                elif fact_type == 'state_check':
                    if len(match) == 2:
                        object_name, state = match
                        fact_name = f"{object_name}_state"
                        preconditions.append(Fact(fact_name, operator, state))
        
        # Try enhanced NLP parsing if available
        enhanced_preconditions = self._enhanced_nlp_parsing(chatbot_response, task_name)
        if enhanced_preconditions:
            preconditions.extend(enhanced_preconditions)
        
        return preconditions
    
    def _enhanced_nlp_parsing(self, chatbot_response: str, task_name: str) -> List[Fact]:
        """
        Enhanced NLP parsing using spaCy or NLTK for better understanding
        """
        try:
            # Try to use spaCy first (more powerful)
            return self._spacy_based_parsing(chatbot_response, task_name)
        except ImportError:
            try:
                # Fallback to NLTK
                return self._nltk_based_parsing(chatbot_response, task_name)
            except ImportError:
                # No NLP libraries available
                return []
    
    def _spacy_based_parsing(self, chatbot_response: str, task_name: str) -> List[Fact]:
        """
        Use spaCy for advanced NLP parsing
        """
        try:
            import spacy
            
            # Load English model (you might want to cache this)
            try:
                nlp = spacy.load("en_core_web_sm")
            except OSError:
                # Try to download if not available
                import subprocess
                subprocess.run(["python", "-m", "spacy", "download", "en_core_web_sm"])
                nlp = spacy.load("en_core_web_sm")
            
            doc = nlp(chatbot_response)
            preconditions = []
            
            # Extract dependency-based preconditions
            for token in doc:
                # Look for requirement patterns
                if token.dep_ == "ROOT" and token.lemma_ in ["need", "require", "must", "should"]:
                    # Find the object being required
                    for child in token.children:
                        if child.dep_ in ["dobj", "pobj"]:
                            # Check if there's a quantity modifier
                            quantity = None
                            for grandchild in child.children:
                                if grandchild.dep_ == "nummod":
                                    try:
                                        quantity = int(grandchild.text)
                                    except ValueError:
                                        continue
                            
                            if quantity is not None:
                                fact_name = f"{child.lemma_}_count"
                                preconditions.append(Fact(fact_name, ">=", quantity))
                            else:
                                fact_name = f"{child.lemma_}_available"
                                preconditions.append(Fact(fact_name, "=", True))
                
                # Look for state conditions
                elif token.dep_ == "nsubj" and token.head.pos_ == "VERB":
                    # Check if this is a state verb
                    if token.head.lemma_ in ["be", "have", "contain"]:
                        for child in token.head.children:
                            if child.dep_ == "attr" or child.dep_ == "dobj":
                                fact_name = f"{token.lemma_}_state"
                                preconditions.append(Fact(fact_name, "=", child.lemma_))
            
            return preconditions
            
        except Exception as e:
            print(f"spaCy parsing failed: {e}")
            return []
    
    def _nltk_based_parsing(self, chatbot_response: str, task_name: str) -> List[Fact]:
        """
        Use NLTK for basic NLP parsing as fallback
        """
        try:
            import nltk
            from nltk.tokenize import word_tokenize, sent_tokenize
            from nltk.tag import pos_tag
            from nltk.chunk import RegexpParser
            
            # Download required NLTK data
            try:
                nltk.data.find('tokenizers/punkt')
            except LookupError:
                nltk.download('punkt')
            try:
                nltk.data.find('taggers/averaged_perceptron_tagger')
            except LookupError:
                nltk.download('averaged_perceptron_tagger')
            
            preconditions = []
            sentences = sent_tokenize(chatbot_response)
            
            for sentence in sentences:
                tokens = word_tokenize(sentence)
                pos_tags = pos_tag(tokens)
                
                # Simple pattern matching with POS tags
                for i, (word, pos) in enumerate(pos_tags):
                    if pos.startswith('VB') and word.lower() in ['need', 'require', 'must']:
                        # Look for the object after the verb
                        if i + 1 < len(pos_tags):
                            next_word, next_pos = pos_tags[i + 1]
                            if next_pos.startswith('NN'):
                                fact_name = f"{next_word}_available"
                                preconditions.append(Fact(fact_name, "=", True))
                
                # Look for "X is Y" patterns
                for i, (word, pos) in enumerate(pos_tags):
                    if pos.startswith('NN') and i + 2 < len(pos_tags):
                        next_word, next_pos = pos_tags[i + 1]
                        next_next_word, next_next_pos = pos_tags[i + 2]
                        if next_pos == 'VBZ' and next_next_pos.startswith('JJ'):
                            fact_name = f"{word}_state"
                            preconditions.append(Fact(fact_name, "=", next_next_word))
            
            return preconditions
            
        except Exception as e:
            print(f"NLTK parsing failed: {e}")
            return []
    
    def _llm_based_precondition_parsing(self, chatbot_response: str, task_name: str) -> List[Fact]:
        """
        LLM-based parsing for complex precondition cases
        """
        try:
            # Load precondition parser prompt
            precondition_prompt = self.precondition_parser_prompt.format(
                task_name=task_name,
                chatbot_response=chatbot_response
            )
            
            response = self.gpt.get_chat_gpt_completion(precondition_prompt)
            
            # Try to parse JSON response
            try:
                import json
                # Extract JSON from response (handle cases where LLM adds extra text)
                json_start = response.find('[')
                json_end = response.rfind(']') + 1
                if json_start != -1 and json_end != -1:
                    json_str = response[json_start:json_end]
                    parsed_data = json.loads(json_str)
                    
                    # Convert to Fact objects
                    facts = []
                    for item in parsed_data:
                        if isinstance(item, dict) and 'name' in item and 'operator' in item and 'value' in item:
                            facts.append(Fact(item['name'], item['operator'], item['value']))
                    
                    return facts
                else:
                    print("LLM response doesn't contain valid JSON array")
                    return []
                    
            except json.JSONDecodeError as e:
                print(f"Failed to parse LLM response as JSON: {e}")
                return []
                
        except Exception as e:
            print(f"LLM-based precondition parsing failed: {e}")
            return []


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
        try:
            for i, method_exec in enumerate(method_execs):
                if method_exec is None or method_exec.method is None:
                    method_strs.append(f"Method {i+1}: [INVALID_METHOD]")
                    continue
                    
                subtasks = []
                for subtask in method_exec.method.subtasks:
                    if subtask is None:
                        subtasks.append("INVALID_SUBTASK")
                    else:
                        subtask_str = f"{subtask.name}({', '.join([str(arg) for arg in subtask.args])})"
                        subtasks.append(subtask_str)
                method_strs.append(f"Method {i+1}: [{', '.join(subtasks)}]")
            available_methods_str = "; ".join(method_strs)
            print(f"DEBUG: Available methods: {available_methods_str}")
        except Exception as e:
            print(f"ERROR formatting methods: {e}")
            available_methods_str = "Error formatting methods"
        
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
            prompt = self.explanation_prompt % (task_str, available_methods_str, current_state_str, chosen_method_str)
            print(f"DEBUG: Generated prompt length: {len(prompt)}")
        
            
            explanation = self.gpt.get_chat_gpt_completion(prompt)
            print(f"DEBUG: Generated explanation length: {len(explanation)}")
            
            # Ensure the explanation contains the expected format
            if "Task:" not in explanation or "Available methods:" not in explanation:
                print("WARNING: GPT response doesn't contain expected format, adding headers...")
                formatted_explanation = f"""Task: {task_str}
                Available methods: {available_methods_str}
                Current state: {current_state_str}
                Chosen method: {chosen_method_str}

                Explanation: {explanation}"""
                return formatted_explanation
            
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
        objects = self.env.get_objects()
        
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
        
        return task_name, task_args



### old functions ###
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
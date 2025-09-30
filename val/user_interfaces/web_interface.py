import socketio
from socketio.exceptions import TimeoutError
from typing import List
from typing import Optional
from pyhtn.htn import Task, Method, Operator, TaskEx, MethodEx, OperatorEx, tree_dict_to_str
from typing import List, Sequence, Optional, Tuple

class WebInterface:
            
    def __init__(self, url="http://localhost:4002"):
        self.sio = socketio.Client()
        self.sio.connect(url)
        self.user_response = None
        self.response_received = False
        self.sio.on('message', self.on_message)

    # This function is called when the client receives a message from the server 
    # change from previous version: event = self.sio.receive(), which is synchronous blocking call to wait for a server event 
    def on_message(self, data):
        print("Received message:", data)
        if isinstance(data, dict) and 'response' in data and data.get('type') == self.expected_type:
            self.user_response = data['response']
            self.response_received = True 
    
    
    def query_next_decomposition_with_edit(self, 
        task_exec: TaskEx, 
        method_execs: Sequence[MethodEx], available_actions: List[str], env_objects: List[str]) -> Tuple[str, MethodEx, Sequence[Optional[float]]]:
        """
        Query user for decomposition choice with edit options
        
        Args:
            task_exec: The task execution to decompose
            method_execs: Available method executions for this task
            available_actions: List of available actions in the environment
            env_objects: List of available objects in the environment
            
        Returns:
            Tuple of (user_choice, chosen_method_exec, rewards)
        """
        print("query_next_decomposition_with_edit called")
        print("task_exec:", task_exec)
        print("method_execs:", method_execs)
        print("method_execs type:", type(method_execs))
        print("method_execs length:", len(method_execs) if method_execs else "None or empty")
        
        self.user_response = None  
        self.response_received = False 
        self.expected_type = 'response_decomposition_with_edit' 
        
        # For NEW_ACTION or unknown tasks, go directly to add_method
        if(method_execs is None or len(method_execs) == 0):
            print("No method_execs available, going to add_method")
            return 'add_method', None, []

        # First, send thinking analysis to chatbot
        head = task_exec.as_dict()
        match = ' '.join(str(m).replace('_', ' ') for m in head['match'])
        task_name = head["name"]
        task_args = [str(m).replace('_', ' ') for m in head['match']]
        
        # Create thinking-style analysis text
        objects_text = ', '.join(env_objects[:5])
        if len(env_objects) > 5:
            objects_text += f" and {len(env_objects) - 5} more..."
        
        # Get subtask names for the analysis
        default_method = method_execs[0] if method_execs else None
        if default_method:
            subtask_names = [f"{s.name}({', '.join([str(arg) for arg in s.args])})" for s in default_method.method.subtasks]
            analysis_text = f"""Thinking...

The game environment contains {objects_text}.

Based on my knowledge and the condition, I will decompose {task_name} to {', '.join(subtask_names)}.

Is it correct?"""
        else:
            analysis_text = f"""Thinking...

The game environment contains {objects_text}.

I need to create a method for {task_name}({', '.join(task_args)}).

Is it correct?"""
        
        # Send thinking analysis
        self.sio.emit('message', {
            'type': 'show_thinking_analysis_and_decomposition',
            'text': {
                'user_task': f"{task_name} {' '.join(task_args)}",
                'task_name': task_name,
                'task_args': task_args,
                'analysis_text': analysis_text
            }
        })
        print(f"Sent thinking analysis for {task_name}")
        
        # Then, send decomposition tree structure
        # Convert method_execs to subtasks format
        subtasks = []
        for method_exec in method_execs:
            method_dict = method_exec.as_dict()
            child_list = method_dict.get("child_data", [])
            
            formatted_children = [
                {
                    "task_name": child["name"],
                    "args": [str(m).replace('_', ' ') for m in child["match"]],
                    "hash": child["id"]
                }
                for child in child_list
            ]
            subtasks.append(formatted_children)
        
        result = {
            "head": {
                "name": head["name"],
                "V": match,
                "hash": head["id"]
            },
            "subtasks": subtasks,
            "available_actions": available_actions,
            "env_objects": env_objects
        }
        
        self.sio.emit('message', {
            'type': 'confirm_best_match_decomposition',
            'text': result
        })
        print("Decomposition tree message emitted")
        
        # Wait for user response from chatbot buttons (Approve/Reject)
        self.user_response = None  
        self.response_received = False 
        self.expected_type = 'response_decomposition_with_edit'
        
        print("Waiting for user response from chatbot...")
        while not self.response_received:
            self.sio.sleep(0.1)
            
        response = self.user_response 
        rewards = [0.0] * len(method_execs)
        user_choice = response.get('user_choice', None)
        response_index = response.get('index', 0)
        
        print("response_index", response_index)
        print("user_choice", user_choice)
        
        # Handle different response types
        if user_choice == 'gui_edit':
            self.last_edited_decomposition = response.get('edited_decomposition', {})
            return user_choice, method_execs[response_index], rewards
        elif user_choice == 'chatbot_edit':
            self.chatbot_response = response.get('chatbot_response', '')
            self.last_preconditions = response.get('preconditions', [])
            return user_choice, method_execs[response_index], rewards
        elif user_choice == 'approve':
            rewards[response_index] = 1.0
            return user_choice, method_execs[response_index], rewards 
        elif user_choice == 'reject':
            # For now, treat reject as add_method - user wants to create new method
            return 'add_method', None, []
        
        # Default to add_method
        return 'add_method', None, []
    
    def display_thinking_analysis(self, user_task: str, task_name: str, task_args: List[str], analysis_text: str):
        """
        Display thinking analysis after grounding in the chatbot
        
        Args:
            user_task: Original user input
            task_name: Extracted task name
            task_args: Extracted task arguments
            analysis_text: Thinking analysis text
        """
        print(f"Displaying thinking analysis for grounding")
        print(f"User task: {user_task}")
        print(f"Extracted: {task_name}({task_args})")
        print(f"Analysis: {analysis_text}")
        
        # Send thinking analysis to frontend chatbot
        self.sio.emit('message', {
            'type': 'display_thinking_analysis',
            'text': {
                'user_task': user_task,
                'task_name': task_name,
                'task_args': task_args,
                'analysis_text': analysis_text
            }
        })

    def display_decomposition_analysis(self, task_name: str, analysis_text: str, subtask_names: List[str], precondition_names: List[str]):
        """
        Display decomposition analysis in the chatbot
        
        Args:
            task_name: Name of the task being analyzed
            analysis_text: Detailed analysis text
            subtask_names: List of subtask names
            precondition_names: List of precondition names
        """
        print(f"Displaying decomposition analysis for {task_name}")
        print(f"Analysis: {analysis_text}")
        print(f"Subtasks: {subtask_names}")
        print(f"Preconditions: {precondition_names}")
        
        # Send analysis to frontend chatbot
        self.sio.emit('message', {
            'type': 'display_decomposition_analysis',
            'text': {
                'task_name': task_name,
                'analysis_text': analysis_text,
                'subtask_names': subtask_names,
                'precondition_names': precondition_names
            }
        })

    def display_edit_options(self, message: str):
        """
        Display edit options in the chatbot
        
        Args:
            message: Message to display to user
        """
        print(f"Displaying edit options: {message}")
        
        # Send edit options to frontend chatbot
        self.sio.emit('message', {
            'type': 'display_edit_options',
            'text': message
        })

    def display_method_creation(self, task_name: str, subtask_names: List[str], precondition_names: List[str]):
        """
        Display method creation process in the chatbot
        
        Args:
            task_name: Name of the task being created
            subtask_names: List of subtask names
            precondition_names: List of precondition names
        """
        print(f"Displaying method creation for {task_name}")
        print(f"Subtasks: {subtask_names}")
        print(f"Preconditions: {precondition_names}")
        
        # Send method creation info to frontend chatbot
        self.sio.emit('message', {
            'type': 'display_method_creation',
            'text': {
                'task_name': task_name,
                'subtask_names': subtask_names,
                'precondition_names': precondition_names
            }
        })

    def display_added_method(self, task_exec: TaskEx, 
        method_exec: MethodEx):
        self.user_response = None  
        self.response_received = False 
        self.expected_type = 'response_decomposition' 
        head = task_exec.as_dict()
        match = ' '.join(str(m).replace('_', ' ') for m in head['match'])

        # Step 2: build subtasks
        subtasks = []
        method_dict = method_exec.as_dict()
        child_list = method_dict.get("child_data", [])
        
        # Convert each child dict to the desired format
        formatted_children = [
            {
                "task_name": child["name"],
                "args": [str(m).replace('_', ' ') for m in child["match"]],
                "hash": child["id"]
            }
            for child in child_list
        ]
        subtasks.append(formatted_children)

        # Step 3: combine everything into one dict
        result = {
            "head": {
                "name": head["name"],
                "V": match,  # Or use a cleaner version if needed
                "hash": head["id"]
            },
            "subtasks": subtasks
        }

        self.user_response = None  
        self.response_received = False

        self.sio.emit('message', {'type': 'display_added_method', 'text': result})
        print("The message is emitted")
        while not self.response_received:
            self.sio.sleep(0.1)
            
        index = self.user_response 
        print("prepared to return")

        return
    
    def check_for_break(self) -> bool:
        return False
        
    
    def display_known_tasks(self, tasks: List[str]):
        text = "\n".join([f"({i}): {task}" for i, task in enumerate(tasks)])
        self.sio.emit('message', {'type': 'display_known_tasks',
                                  'text': "Those are the actions I know:" + text})
        return


    def display_method_creation(self, message: str, task_name: str = None, subtasks: List[str] = None, preconditions: List[str] = None):
        """
        Display when a new method is being created
        Args:
            message: Simple message to display
            task_name: The task name (optional)
            subtasks: List of subtasks (optional)
            preconditions: List of preconditions (optional)
        """
        if task_name and subtasks:
            # Full method creation display
            subtasks_text = ", ".join(subtasks)
            creation_text = f"⚙️ **Creating New Method:** `{task_name}`\n\n**Subtasks:** {subtasks_text}"
            
            if preconditions and len(preconditions) > 0:
                creation_text += f"\n\n**Preconditions:** {', '.join(preconditions)}"
        else:
            # Simple message display
            creation_text = f"⚙️ **Add New Method**\n\n{message}"
        
        self.sio.emit('message', {'type': 'display_method_creation', 'text': creation_text})
        print("Method creation message emitted")
        return

    def display_edit_options(self, message: str):
        """
        Display editing options for existing decompositions
        Args:
            message: Message to display
        """
        self.sio.emit('message', {'type': 'display_edit_options', 'text': f"✏️ **Edit Decomposition**\n\n{message}"})
        print("Edit options message emitted")
        return

    # def display_edit_options_old(self, task_exec, method_execs):
    #     """
    #     Display editing options for existing decompositions
    #     Args:
    #         task_exec: The task being edited
    #         method_execs: Available method executions
    #     """
    #     # Format the task
    #     head = task_exec.as_dict()
    #     task_name = head["name"]
    #     match = ' '.join(str(m).replace('_', ' ') for m in head['match'])
        
    #     # Format available methods
    #     methods_text = []
    #     for i, method_exec in enumerate(method_execs):
    #         method_dict = method_exec.as_dict()
    #         child_list = method_dict.get("child_data", [])
    #         subtasks = [f"{child['name']}({', '.join([str(m).replace('_', ' ') for m in child['match']])})" 
    #                    for child in child_list]
    #         methods_text.append(f"Option {i+1}: {', '.join(subtasks)}")
        
    #     edit_text = f"Editing options for {task_name}({match}):\n" + "\n".join(methods_text)
        
    #     self.sio.emit('message', {'type': 'display_edit_options', 'text': edit_text})
    #     print("Edit options message emitted")
    #     return
    
    def request_user_task(self) -> str:
        self.user_response = None  
        self.response_received = False 
        self.sio.emit('message', {'type': 'request_user_task', 'text': 'How can I help you today?'})
        print("The message is emitted")
        self.expected_type = 'confirm_response'
        while not self.response_received:
            self.sio.sleep(0.1)
        print('received')
        return self.user_response 
    
    def ask_subtasks(self, user_task: str) -> str:
        self.user_response = None  
        self.response_received = False 
        self.expected_type = 'confirm_response'
        self.sio.emit('message', {'type': 'ask_subtasks', 
                                  'text': f"What are the steps for completing the task '{user_task}'?"})
        while not self.response_received:
            self.sio.sleep(0.1)
        print('received response:', self.user_response)
        return self.user_response
    
    def ask_rephrase(self, user_tasks: str) -> str:
        self.user_response = None  
        self.response_received = False
        self.expected_type = 'confirm_response' 
        self.sio.emit('message', {
            'type': 'ask_rephrase', 
            'text': f"Sorry about that. Can you rephrase the tasks '{user_tasks}'?"
        })
        while not self.response_received:
            self.sio.sleep(0.1)
        print('received response:', self.user_response)
        return self.user_response

    def segment_confirmation(self, steps: List[str]) -> bool:
        # set to None to reset the stored user response
        self.user_response = None
        self.response_received = False
        self.expected_type = 'confirm_response' 
        formatted_steps = ', '.join(steps)
        self.sio.emit('message', {'type': 'segment_confirmation', 
                                  'text': f"These are the individual steps of your command: '{formatted_steps}', right?",
                                  'steps': steps})
        while not self.response_received:
            self.sio.sleep(0.1)
        print('received response:', self.user_response)
        return 'yes' == self.user_response

    def correct_grounding(self, user_task: str, task_name: str, task_args: List[str], env_objects: List[str], available_actions: List[str]) -> tuple[str, List[str]]:
        """
        Allow user to correct the grounding result (action and objects)
        Returns (corrected_task_name, corrected_task_args)
        """
        self.user_response = None  
        self.response_received = False 
        self.expected_type = 'correct_grounding_response'
        env_objects=list(set(env_objects))
        available_actions=list(set(available_actions))
        self.sio.emit('message', {
            'type': 'correct_grounding',
            'text': f"Correct the grounding for: '{user_task}'",
            'current_action': task_name,
            'current_objects': task_args,
            'available_objects': env_objects,
            'available_actions': available_actions
        })
        
        while not self.response_received:
            self.sio.sleep(0.1)
        
        # Parse response - expected format: "action:object1,object2"
        response = self.user_response
        if ':' in response:
            corrected_task_name, objects_str = response.split(':', 1)
            corrected_task_args = [obj.strip() for obj in objects_str.split(',') if obj.strip()]
        else:
            corrected_task_name = task_name
            corrected_task_args = task_args
        
        # After grounding correction, just return
        # Both thinking analysis and decomposition tree will be shown together in the main loop
        return corrected_task_name, corrected_task_args

    def show_thinking_analysis_and_decomposition_after_correction_OLD_BACKUP(self, user_task: str, task_name: str, task_args: List[str], available_actions: List[str], env_objects: List[str]):
        """
        Show thinking analysis and decomposition tree after grounding correction
        """
        # First show thinking analysis
        self.sio.emit('message', {
            'type': 'show_thinking_analysis_and_decomposition',
            'text': {
                'user_task': user_task,
                'task_name': task_name,
                'task_args': task_args
            }
        })
        
        # Then show decomposition tree - we need to check if there are existing decompositions
        try:
            from pyhtn.htn import Task, TaskEx
            
            # Create a basic task structure for display
            task = Task(task_name, args=task_args)
            
            # Try to get existing method_execs for this task
            # This should be similar to what happens in the main planning loop
            method_execs = []
            try:
                # Create a temporary task execution to check for methods
                state = self.env.get_state()
                task_exec = TaskEx(task, state, match=task_args)
                
                # Try to get method executions for this task
                if hasattr(self, 'htn_interface') and self.htn_interface:
                    method_execs = self.htn_interface.get_method_execs_for_task(task_exec)
                    print(f"Found {len(method_execs)} existing method_execs for task {task_name}")
                else:
                    print("No htn_interface available, using empty method_execs")
            except Exception as e:
                print(f"Could not get method_execs: {e}")
                method_execs = []
            
            # Convert method_execs to subtasks format (similar to query_next_decomposition_with_edit)
            subtasks = []
            if method_execs and len(method_execs) > 0:
                for method_exec in method_execs:
                    method_dict = method_exec.as_dict()
                    child_list = method_dict.get("child_data", [])
                    
                    formatted_children = [
                        {
                            "task_name": child["name"],
                            "args": [str(m).replace('_', ' ') for m in child["match"]],
                            "hash": child["id"]
                        }
                        for child in child_list
                    ]
                    subtasks.append(formatted_children)
                print(f"Created {len(subtasks)} subtask groups")
            else:
                print("No existing method_execs found, showing empty structure")
            
            # Create the result structure
            result = {
                "head": {
                    "name": task_name,
                    "V": ' '.join(task_args) if task_args else '',
                    "hash": f"{task_name}_{hash(' '.join(task_args))}"
                },
                "subtasks": subtasks,
                "available_actions": available_actions,
                "env_objects": env_objects
            }
            
            # Send decomposition tree structure
            self.sio.emit('message', {
                'type': 'confirm_best_match_decomposition',
                'text': result
            })
            print(f"Sent decomposition tree for task: {task_name}({task_args}) with {len(subtasks)} subtask groups")
            
        except Exception as e:
            print(f"Error creating decomposition tree: {e}")
            # Fallback: just send a basic message
            self.sio.emit('message', {
                'type': 'show_thinking_analysis_and_decomposition',
                'text': {
                    'user_task': user_task,
                    'task_name': task_name,
                    'task_args': task_args,
                    'error': str(e)
                }
            })


# ### previous version ###
#     def map_confirmation(self, user_task: str, task_name: str) -> bool:
#         if self.disable_map_confirmation:
#             return True 
#         self.user_response = None  
#         self.response_received = False 
#         self.expected_type = 'confirm_response' 
#         self.sio.emit('message', {
#             'type': 'map_confirmation', 
#             'text': f"I think that '{user_task}' is the action '{task_name}'. Is that right?"
#         })
#         while not self.response_received:
#             self.sio.sleep(0.1)
#         print('received response:', self.user_response)
#         return 'yes' == self.user_response

#     def map_correction(self, user_task: str, known_tasks: List[str]) -> Optional[int]:
#         known_tasks.append('None of these above')
#         self.user_response = None  
#         self.response_received = False 
#         self.expected_type = 'confirm_response' 
#         self.sio.emit('message', {
#             'type': 'map_correction',
#             'text': f"Which of these is the best choice for '{user_task}'?", 
#             'user_task': user_task,
#             'known_tasks': known_tasks
#         })
#         while not self.response_received:
#             self.sio.sleep(0.1)
#         print('received response:', self.user_response)
#         response = int(self.user_response)
#         if response == len(known_tasks) - 1:
#             print("none")
#             return None
#         return response

#     def map_new_method_confirmation(self, user_task: str) -> bool:
#         if self.disable_map_new_method_confirmation:
#             return True
#         self.user_response = None  
#         self.response_received = False
#         self.expected_type = 'confirm_response'  
#         self.sio.emit('message', {
#             'type': 'map_new_method_confirmation',
#             'text': f"The task '{user_task}' is a new method. Is that right?"
#         })
#         while not self.response_received:
#             self.sio.sleep(0.1)
#         print('received response:', self.user_response)
#         return 'yes' == self.user_response

#     def ground_confirmation(self, task_name: str, task_args: List[str]) -> bool:
#         if self.disable_ground_confirmation:
#             return True 
#         self.user_response = None  
#         self.response_received = False
#         self.expected_type = 'confirm_response'  
#         self.sio.emit('message', {
#             'type': 'ground_confirmation',
#             'task_name': task_name,
#             'task_args': ', '.join(task_args),
#             'text': f"The task is {task_name}({task_args}). Is that right? "
#         })
#         while not self.response_received:
#             self.sio.sleep(0.1)
#         print('received response:', self.user_response)
#         return 'yes' == self.user_response

#     def ground_correction(self, task_name: str, task_args: List[str], env_objects: List[str]) -> List[str]:
#         self.user_response = None  
#         self.response_received = False 
#         self.expected_type = 'confirm_response' 
#         self.sio.emit('message', {
#             'type': 'ground_correction',
#             'text': f"Could you help me pick the actual object? {task_name}",
#             'task_args': task_args,
#             'env_objects': env_objects
#         })
#         while not self.response_received:
#             self.sio.sleep(0.1)
#         print('received response:', self.user_response)
#         return self.user_response

#     def gen_confirmation(self, user_task: str, task_name: str, task_args: List[str]) -> bool:
#         if self.disable_gen_confirmation:
#             return True
#         self.user_response = None  
#         self.response_received = False 
#         self.expected_type = 'confirm_response' 
#         formatted_args = ', '.join(task_args)
#         self.sio.emit('message', {
#             'type': 'gen_confirmation',
#             'text': f"{user_task} is {task_name}({formatted_args}). Is that right?",
#             'task_args': task_args
#         })
#         while not self.response_received:
#             self.sio.sleep(0.1)
#         print('received response:', self.user_response)
#         return 'yes' == self.user_response

#     def gen_correction(self, task_name: str, task_args: List[str], env_objects: List[str]) -> List[str]:
#         self.user_response = None  
#         self.response_received = False 
#         self.expected_type = 'confirm_response' 
#         self.sio.emit('message', {
#             'type': 'gen_correction',
#             'text': f"Could you help me pick the actual object? {task_name}:",
#             'task_args': task_args,
#             'env_objects': env_objects
#         })
#         while not self.response_received:
#             self.sio.sleep(0.1)
#         print('received response:', self.user_response)
#         return self.user_response

#     def confirm_task_execution(self, user_task: str) -> bool:
#         if self.disable_confirm_task_execution:
#             return True
#         self.user_response = None  
#         self.response_received = False 
#         self.expected_type = 'confirm_response' 
#         self.sio.emit('message', {
#             'type': 'confirm_task_execution',
#             'text': f"Should I execute {user_task}?"
#         })
#         while not self.response_received:
#             self.sio.sleep(0.1)
#         print('received response:', self.user_response)
#         return 'yes' == self.user_response
    

    
#     def correct_decomposition(self, task_str: str, method_options: List[str], 
#                            chosen_method_exec, method_execs) -> tuple:
#         """
#         Allow user to correct the decomposition choice
#         Returns (corrected_method_exec, corrected_rewards)
#         """
#         self.user_response = None  
#         self.response_received = False 
#         self.expected_type = 'correct_decomposition_response'
        
#         self.sio.emit('message', {
#             'type': 'correct_decomposition',
#             'text': f"Correct the decomposition for: {task_str}",
#             'method_options': method_options,
#             'current_choice': method_execs.index(chosen_method_exec) if chosen_method_exec in method_execs else -1
#         })
        
#         while not self.response_received:
#             self.sio.sleep(0.1)
        
#         # Parse response - expected format: "method_index:reward"
#         response = self.user_response
#         if ':' in response:
#             method_index_str, reward_str = response.split(':', 1)
#             try:
#                 method_index = int(method_index_str)
#                 reward = float(reward_str)
#                 if 0 <= method_index < len(method_execs):
#                     corrected_method_exec = method_execs[method_index]
#                     corrected_rewards = [None] * len(method_execs)
#                     corrected_rewards[method_index] = reward
#                     return corrected_method_exec, corrected_rewards
#             except (ValueError, IndexError):
#                 pass
        
#         # Return original choice if parsing fails
#         rewards = [None] * len(method_execs)
#         if chosen_method_exec in method_execs:
#             rewards[method_execs.index(chosen_method_exec)] = 1.0
#         return chosen_method_exec, rewards
    
if __name__ == "__main__":
    web_interface = WebInterface()
    print(web_interface.query_next_decomposition_and_rewards(
        TaskEx("task1", "arg1"),
        [MethodEx("method1", "arg1"), MethodEx("method2", "arg2")]
    ))


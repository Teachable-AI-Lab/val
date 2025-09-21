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
        method_execs: Sequence[MethodEx], available_actions: List[str], env_objects: List[str]) -> Tuple[MethodEx, Sequence[Optional[float]]]:
        """
        Enhanced version that allows users to edit decomposition options
        Supports two edit modes:
        1. GUI edit: User edits directly in the interface
        2. Chatbot edit: User responds via chatbot (triggers query_new_method_exec)
        Returns (chosen_or_edited_method_exec, rewards)
        """
        self.user_response = None  
        self.response_received = False 
        self.expected_type = 'response_decomposition_with_edit' 
        env_objects=list(set(env_objects))
        available_actions=list(set(available_actions))
        # Skip if there are no method_execs 
        if(method_execs is None or len(method_execs) == 0):
            user_choice = 'add_method'
            return user_choice, None, []
        else:
            ##### convert format ##### 
            # Step 1: get head
            head = task_exec.as_dict()
            match = ' '.join(str(m).replace('_', ' ') for m in head['match'])

            # Step 2: build subtasks
            subtasks = []
            for method_exec in method_execs:
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
                    "V": match,  
                    "hash": head["id"]
                },
                "subtasks": subtasks,
                "available_actions": available_actions,
                "env_objects": env_objects
            }

            self.user_response = None  
            self.response_received = False

            self.sio.emit('message', {'type': 'confirm_best_match_decomposition', 'text': result})
            print("The message is emitted")
            while not self.response_received:
                self.sio.sleep(0.1)
                
            response = self.user_response 
            rewards = [None]*len(method_execs)
            user_choice=response.get('user_choice', None)
            # Handle different response types
            if user_choice == 'gui_edit':
                    # User edited via GUI - return None to trigger new method creation from edited content
                self.last_edited_decomposition = response.get('edited_decomposition', {})
                return user_choice, None, []
            elif user_choice == 'chatbot_edit':
                    # User responded via chatbot - this triggers query_new_method_exec flow
                self.chatbot_response = response.get('chatbot_response', '')
                self.last_preconditions = response.get('preconditions', [])
                return user_choice, None, []
            elif user_choice == "add_method":
                return user_choice, None, []
            elif user_choice == 'approve':
                # Legacy support for simple index
                response_index = response.get('index', None)
                print("response_index", response_index)
                rewards[response_index] = 1.0
                return user_choice, method_execs[response_index], rewards 
            user_choice = 'add_method'
            return user_choice, None, []
    

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

    def display_decomposition_analysis(self, task_name: str, chatbot_response: str, subtasks: List[str], preconditions: List[str] = None):
        """
        Display the complete decomposition analysis including precondition analysis and thinking process
        Args:
            task_name: The task being decomposed
            chatbot_response: Original chatbot response
            subtasks: List of subtasks
            preconditions: List of preconditions (optional)
        """
        # Format subtasks
        subtasks_text = ", ".join(subtasks)
        
        # Build comprehensive analysis message
        analysis_parts = []
        
        # Add precondition analysis
        if preconditions and len(preconditions) > 0:
            analysis_parts.append(f"🔍 **Precondition Analysis:** Found conditions: {', '.join(preconditions)}")
        else:
            analysis_parts.append("🔍 **Precondition Analysis:** No specific conditions found")
        
        # Add thinking process
        analysis_parts.append(f"🧠 **Thinking Process:** Learned that `{task_name}` should be decomposed to: {subtasks_text}")
        
        # Combine all parts
        analysis_text = "\n\n".join(analysis_parts)
        
        self.sio.emit('message', {'type': 'display_decomposition_analysis', 'text': analysis_text})
        print("Decomposition analysis message emitted")
        return

    # def display_method_creation(self, task_name: str, subtasks: List[str], preconditions: List[str] = None):
    #     """
    #     Display when a new method is being created
    #     Args:
    #         task_name: The task name
    #         subtasks: List of subtasks
    #         preconditions: List of preconditions (optional)
    #     """
    #     subtasks_text = ", ".join(subtasks)
    #     creation_text = f"⚙️ **Creating New Method:** `{task_name}`\n\n**Subtasks:** {subtasks_text}"
        
    #     if preconditions and len(preconditions) > 0:
    #         creation_text += f"\n\n**Preconditions:** {', '.join(preconditions)}"
        
    #     self.sio.emit('message', {'type': 'display_method_creation', 'text': creation_text})
    #     print("Method creation message emitted")
    #     return

    # def display_edit_options(self, task_exec, method_execs):
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
            
        return corrected_task_name, corrected_task_args


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
    

import socketio
from socketio.exceptions import TimeoutError
from typing import List
from typing import Optional
from pyhtn.htn import Task, Method, Operator, TaskEx, MethodEx, OperatorEx, tree_dict_to_str
from typing import List, Sequence, Optional, Tuple

class WebInterface:
            
    def __init__(self, url="http://localhost:4002",
                 disable_segment_confirmation: bool = False, disable_map_confirmation: bool = False,
                 disable_map_correction: bool = False, disable_map_new_method_confirmation: bool = False, 
                 disable_ground_confirmation: bool = False, disable_ground_correction: bool = False,
                 disable_gen_confirmation: bool = False, disable_gen_correction: bool = False,
                 disable_confirm_task_decomposition: bool = True, disable_confirm_task_execution: bool = True,
                 next_select_kind = "all at once"):
        self.sio = socketio.Client()
        self.sio.connect(url)
        self.user_response = None
        self.response_received = False
        self.sio.on('message', self.on_message)
        self.disable_segment_confirmation = disable_segment_confirmation
        self.disable_map_confirmation = disable_map_confirmation
        self.disable_map_correction = disable_map_correction
        self.disable_map_new_method_confirmation = disable_map_new_method_confirmation
        self.disable_ground_confirmation = disable_ground_confirmation
        self.disable_ground_correction = disable_ground_correction
        self.disable_gen_confirmation = disable_gen_confirmation
        self.disable_gen_correction = disable_gen_correction
        self.disable_confirm_task_decomposition = disable_confirm_task_decomposition
        self.disable_confirm_task_execution = disable_confirm_task_execution
        self.next_select_kind = next_select_kind

    # This function is called when the client receives a message from the server 
    # change from previous version: event = self.sio.receive(), which is synchronous blocking call to wait for a server event 
    def on_message(self, data):
        print("Received message:", data)
        if isinstance(data, dict) and 'response' in data and data.get('type') == self.expected_type:
            self.user_response = data['response']
            self.response_received = True 
    
    def query_next_decomposition_and_rewards(self, 
        task_exec: TaskEx, 
        method_execs: Sequence[MethodEx]) -> Tuple[MethodEx, Sequence[Optional[float]]]:
        self.user_response = None  
        self.response_received = False 
        self.expected_type = 'response_decomposition' 
        
        # Skip if there are no method_execs 
        if(method_execs is None or len(method_execs) == 0):
            head = task_exec.as_dict()
            match = ' '.join(str(m).replace('_', ' ') for m in head['match'])
            subtasks = []
            result = {
            "head": {
                "name": head["name"],
                "V": match,  # Or use a cleaner version if needed
                "hash": head["id"]
            },
            "subtasks": subtasks
            }
            self.sio.emit('message', {'type': 'confirm_best_match_decomposition', 'text': result})
            print("The message is emitted")
            while not self.response_received:
                self.sio.sleep(0.1)       
            index = self.user_response
            print("index", index) 
            print("index type", type(index))
            return None, []
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
                        "Task": ' '.join([child["name"]] + [str(m).replace('_', ' ') for m in child["match"]]),
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

            self.sio.emit('message', {'type': 'confirm_best_match_decomposition', 'text': result})
            print("The message is emitted")
            while not self.response_received:
                self.sio.sleep(0.1)
                
            index = self.user_response 
            rewards = [None]*len(method_execs)
            if index == "add method":
                return None, []
            if(self.next_select_kind == "one at a time"):
                for i, method_exec in enumerate(method_execs):
                    confirmed = self._confirm_task_decomposition(task_exec, method_exec)
                    if(not confirmed):
                        rewards[i] = -1.0
                    else:
                        rewards[i] = 1.0
                        return method_exec, rewards 
            else:
                rewards[index] = 1.0
                return method_execs[index], rewards 
    
    def display_added_method(self, task_exec: TaskEx, 
        method_exec: MethodEx):
        self.user_response = None  
        self.response_received = False 
        self.expected_type = 'response_decomposition' 
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
                "Task": ' '.join([child["name"]] + [str(m).replace('_', ' ') for m in child["match"]]),
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

        return
    
    def check_for_break(self) -> bool:
        return False
        
    def edit_decomposition(self,best_match_decomposition):
        """
        add_step()
        delete_step()
        change_order()
        change_pred()
        change_arg()
    
        """
        self.sio.emit('message', {'type': 'edit_decomposition', 
                                  'text': best_match_decomposition})
        print('sent confirmation')
        event = self.sio.receive()
        print('received event:', event[1])
        return
    
    def display_known_tasks(self, tasks: List[str]):
        text = "\n".join([f"({i}): {task}" for i, task in enumerate(tasks)])
        self.sio.emit('message', {'type': 'display_known_tasks',
                                  'text': "Those are the actions I know:" + text})
        return
    
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
    
    def map_confirmation(self, user_task: str, task_name: str) -> bool:
        if self.disable_map_confirmation:
            return True 
        self.user_response = None  
        self.response_received = False 
        self.expected_type = 'confirm_response' 
        self.sio.emit('message', {
            'type': 'map_confirmation', 
            'text': f"I think that '{user_task}' is the action '{task_name}'. Is that right?"
        })
        while not self.response_received:
            self.sio.sleep(0.1)
        print('received response:', self.user_response)
        return 'yes' == self.user_response

    def map_correction(self, user_task: str, known_tasks: List[str]) -> Optional[int]:
        known_tasks.append('None of these above')
        self.user_response = None  
        self.response_received = False 
        self.expected_type = 'confirm_response' 
        self.sio.emit('message', {
            'type': 'map_correction',
            'text': f"Which of these is the best choice for '{user_task}'?", 
            'user_task': user_task,
            'known_tasks': known_tasks
        })
        while not self.response_received:
            self.sio.sleep(0.1)
        print('received response:', self.user_response)
        response = int(self.user_response)
        if response == len(known_tasks) - 1:
            print("none")
            return None
        return response

    def map_new_method_confirmation(self, user_task: str) -> bool:
        if self.disable_map_new_method_confirmation:
            return True
        self.user_response = None  
        self.response_received = False
        self.expected_type = 'confirm_response'  
        self.sio.emit('message', {
            'type': 'map_new_method_confirmation',
            'text': f"The task '{user_task}' is a new method. Is that right?"
        })
        while not self.response_received:
            self.sio.sleep(0.1)
        print('received response:', self.user_response)
        return 'yes' == self.user_response

    def ground_confirmation(self, task_name: str, task_args: List[str]) -> bool:
        if self.disable_ground_confirmation:
            return True 
        self.user_response = None  
        self.response_received = False
        self.expected_type = 'confirm_response'  
        self.sio.emit('message', {
            'type': 'ground_confirmation',
            'task_name': task_name,
            'task_args': ', '.join(task_args),
            'text': f"The task is {task_name}({task_args}). Is that right? "
        })
        while not self.response_received:
            self.sio.sleep(0.1)
        print('received response:', self.user_response)
        return 'yes' == self.user_response

    def ground_correction(self, task_name: str, task_args: List[str], env_objects: List[str]) -> List[str]:
        self.user_response = None  
        self.response_received = False 
        self.expected_type = 'confirm_response' 
        self.sio.emit('message', {
            'type': 'ground_correction',
            'text': f"Could you help me pick the actual object? {task_name}",
            'task_args': task_args,
            'env_objects': env_objects
        })
        while not self.response_received:
            self.sio.sleep(0.1)
        print('received response:', self.user_response)
        return self.user_response

    def gen_confirmation(self, user_task: str, task_name: str, task_args: List[str]) -> bool:
        if self.disable_gen_confirmation:
            return True
        self.user_response = None  
        self.response_received = False 
        self.expected_type = 'confirm_response' 
        formatted_args = ', '.join(task_args)
        self.sio.emit('message', {
            'type': 'gen_confirmation',
            'text': f"{user_task} is {task_name}({formatted_args}). Is that right?",
            'task_args': task_args
        })
        while not self.response_received:
            self.sio.sleep(0.1)
        print('received response:', self.user_response)
        return 'yes' == self.user_response

    def gen_correction(self, task_name: str, task_args: List[str], env_objects: List[str]) -> List[str]:
        self.user_response = None  
        self.response_received = False 
        self.expected_type = 'confirm_response' 
        self.sio.emit('message', {
            'type': 'gen_correction',
            'text': f"Could you help me pick the actual object? {task_name}:",
            'task_args': task_args,
            'env_objects': env_objects
        })
        while not self.response_received:
            self.sio.sleep(0.1)
        print('received response:', self.user_response)
        return self.user_response

    def confirm_task_execution(self, user_task: str) -> bool:
        if self.disable_confirm_task_execution:
            return True
        self.user_response = None  
        self.response_received = False 
        self.expected_type = 'confirm_response' 
        self.sio.emit('message', {
            'type': 'confirm_task_execution',
            'text': f"Should I execute {user_task}?"
        })
        while not self.response_received:
            self.sio.sleep(0.1)
        print('received response:', self.user_response)
        return 'yes' == self.user_response
    
if __name__ == "__main__":
    web_interface = WebInterface()
    print(web_interface.query_next_decomposition_and_rewards(
        TaskEx("task1", "arg1"),
        [MethodEx("method1", "arg1"), MethodEx("method2", "arg2")]
    ))
    

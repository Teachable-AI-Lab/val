import json
from typing import List, Sequence, Optional, Tuple
from time import sleep

import websocket

from val.utils import Task
from val.user_interfaces.abstract_interface import AbstractUserInterface
from pyhtn.htn import Task, Method, Operator, TaskEx, MethodEx, OperatorEx, tree_dict_to_str


class SpeechInterface(AbstractUserInterface):
    
    def __init__(self, disable_segment_confirmation: bool = False, disable_map_confirmation: bool = False,
                 disable_map_correction: bool = False, disable_map_new_method_confirmation: bool = False, 
                 disable_ground_confirmation: bool = False, disable_ground_correction: bool = False,
                 disable_gen_confirmation: bool = False, disable_gen_correction: bool = False,
                 disable_confirm_task_decomposition: bool = False, disable_confirm_task_execution: bool = False, 
                 next_select_kind = "one at a time", url='ws://localhost:3000/metro'

                 ):
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
        self.url = url
        self.ws = websocket.create_connection(self.url)

    
    def get_state(self):
        state = self.send_and_recv({"command":"get_state", "game_id": 0})
        return state
    
    def send_and_recv(self, message: dict):
        sleep(0.25)
        message = json.dumps(message)
        attempts = 0
        while attempts < 3:
            try:
                self.ws.send(message)
                result = self.ws.recv()
                return json.loads(result)
            except:
                print(attempts)
                attempts = attempts + 1
                self.ws = websocket.create_connection(self.url)

        print("Failed")
        return None
    
    def send_msg(self, msg):
        command = {"command":"speak", "response": msg}
        res = self.send_and_recv(command)
        if res is None:
            raise NotImplementedError #TODO: figure out how to best handle a poor connection. Try many times? Quit? Something else?
        elif res["Status"] != "Success":
            raise NotImplementedError
        else:
            return True
    
    def get_instructions(self):
        while True:
            state = self.get_state()
            if state["new_instructions"] == True:
                return state["instruction_text"]
        
        
    def check_for_break(self) -> bool:
        return False
    
    def update_graph_vis(self, root_task_exec):
        tree_dict = root_task_exec.tree_to_dict()
        # pprint(tree_dict, sort_dicts=False)
        print('---- HTN Graph Visualization ----')
        print(tree_dict)
        print('----          end            ----')

    def _confirm_task_decomposition(self, task_exec, method_exec):
        if self.disable_confirm_task_decomposition:
            return True
        subtask_execs =  method_exec.subtask_execs

        subtasks_str = f"[{', '.join([x.fn_str() for x in subtask_execs])}]"

        while True:
            user_msg = f"Should I decompose { task_exec.fn_str() } to { subtasks_str }?. Please respond yes or no."
            self.send_msg(user_msg)
            users_choice = self.get_instructions()
            users_choice = users_choice.lower().strip()
            if users_choice in ['yes', 'no']:
                break
            err_msg = "Invalid input. Please say yes or no"
            self.send_msg(err_msg)
        return users_choice == 'yes'

    def _select_task_decomposition(self, task_exec, method_execs):
        print(f"\nMain Task: {task_exec}\n")
        print("Choose a task decomposition method:")

        for i, method_exec in enumerate(method_execs):
            subtask_execs =  method_exec.subtask_execs
            option = chr(ord('a') + i)
            print(f"  {option}) {subtask_execs}")
            
        #print("\nEnter the letter of the decomposition to select it (e.g., a, b, c), or type 'NA' to skip:")
        while True:
            user_msg = "Say the letter of the decomposition to select it (e.g., a, b, c), or say 'NA' to skip:"
            self.send_msg(user_msg)
            user_input = self.get_instructions()
            user_input = user_input.lower().strip()
            if user_input == 'na':
                return None
            elif len(user_input) == 1 and 'a' <= user_input <= chr(ord('a') + len(subtask_execs) - 1):
                return ord(user_input) - ord('a')
            else:
                err_msg = "Invalid input. Please say a valid option (a, b, ...) or 'NA'."
                self.send_msg(err_msg)

    
    def query_next_decomposition_and_rewards(self, 
        task_exec: TaskEx, 
        method_execs: Sequence[MethodEx]) -> Tuple[MethodEx, Sequence[Optional[float]]]:

        if(method_execs is None or len(method_execs) == 0):
            return None, []

        rewards = [None]*len(method_execs)
        if(self.next_select_kind == "one at a time"):
            for i, method_exec in enumerate(method_execs):
                confirmed = self._confirm_task_decomposition(task_exec, method_exec)
                if(not confirmed):
                    rewards[i] = -1.0
                else:
                    rewards[i] = 1.0
                    return method_exec, rewards 
        else:
            index = self._select_task_decomposition(task_exec, method_execs)
            rewards[index] = 1.0
            return method_execs[index], rewards 
        
    
    def display_added_method(self, task_exec: TaskEx, method_exec: MethodEx) -> None: 
        print("Added Decomposition Method:")
        print(f"Main Task: {task_exec.task.name}")
        print("Subtasks:")
        for i, subtask in enumerate(method_exec.method.subtasks, start=1):
            print(f"  {i}. {subtask.name}")

               
    def request_user_task(self) -> str:
        user_msg = "How can I help you today?"
        self.send_msg(user_msg)
        user_task = self.get_instructions()
        user_task = user_task.lower().strip()
        return user_task

    def ask_subtasks(self, user_task: str) -> str:
        user_msg = f"What are the steps for completing the task '{user_task}'?"
        self.send_msg(user_msg)
        steps = self.get_instructions()
        steps = steps.lower().strip()
        return steps

    def ask_rephrase(self, user_tasks: str) -> str:
        # TODO ask step by step or rephrase as a whole? should we
        # include options: "add more steps/yes/no"?
        user_msg = f"Sorry about that. Can you rephrase the tasks '{user_tasks}'?"
        self.send_msg(user_msg)
        rephrased_user_tasks = self.get_instructions()
        rephrased_user_tasks = rephrased_user_tasks.lower().strip()
        return rephrased_user_tasks

    def segment_confirmation(self, steps: List[str]) -> bool:
        if self.disable_segment_confirmation:
            return True   
        [print(index,step) for index, step in enumerate(steps, start=1)]
        while True:
            user_msg = f"These steps on the screen are the individual steps of your command, right?. Please respond yes or no."
            self.send_msg(user_msg)
            users_choice = self.get_instructions()
            users_choice = users_choice.lower().strip()
            if users_choice in ['yes', 'no']:
                break
            err_msg = "Invalid input. Please say yes or no"
            self.send_msg(err_msg)
        return users_choice == 'yes'

    def map_confirmation(self, user_task: str, task_name: str) -> bool:
        if self.disable_map_confirmation:
            return True 
        while True:
            user_msg = f"I think that '{user_task}' is the action '{task_name}'. Is that right??. Please respond yes or no."
            self.send_msg(user_msg)
            users_choice = self.get_instructions()
            users_choice = users_choice.lower().strip()
            if users_choice in ['yes', 'no']:
                break
            err_msg = "Invalid input. Please say yes or no"
            self.send_msg(err_msg)
        return users_choice == 'yes'

    def map_correction(self, user_task: str, known_tasks: List[str]) -> Optional[int]:
        print(f"Which of these is the best choice for '{user_task}'?")
        for i, task in enumerate(known_tasks):
            print(f"({chr(ord('a')+i)}): {task}")

        choices=[chr(ord('a')+i) for i in range(len(known_tasks))]
        while True:
            user_msg = f"Please refer to the screen. Please say which of these is the best choice for '{user_task}'. Choices include {choices}:"
            self.send_msg(user_msg)
            users_choice = self.get_instructions()
            users_choice = users_choice.lower().strip()
            if users_choice.lower() in choices:
                break
            err_msg = f"Invalid input. Please say {choices}"
            self.send_msg(err_msg)
        users_choice_int=ord(users_choice)-ord('a')
        return users_choice_int if users_choice_int < len(known_tasks) else None

    def map_new_method_confirmation(self, user_task: str) -> bool:
        if self.disable_map_new_method_confirmation:
            return True
        while True:
            user_msg = f"The task '{user_task}' is a new method. Is that right? Please respond yes or no."
            self.send_msg(user_msg)
            users_choice = self.get_instructions()
            users_choice = users_choice.lower().strip()
            if users_choice in ['yes', 'no']:
                break
            err_msg = "Invalid input. Please say yes or no"
            self.send_msg(err_msg)
        return users_choice == 'yes'

    def ground_confirmation(self, task_name: str, task_args: List[str]) -> bool:       
        if self.disable_ground_confirmation:
            return True 
        formatted_args = ', '.join(task_args)
        while True:
            user_msg = f"The task is {task_name}({formatted_args}). Is that right? Please respond yes or no."
            self.send_msg(user_msg)
            users_choice = self.get_instructions()
            users_choice = users_choice.lower().strip()
            if users_choice in ['yes', 'no']:
                break
            err_msg = "Invalid input. Please say yes or no"
            self.send_msg(err_msg)
        return users_choice == 'yes'

    def ground_correction(self, task_name: str, task_args: List[str],
                          env_objects: List[str]) -> List[str]: #TODO Figure out how to fix this for speech to text user interface
        numbered_env_objects = [f"{i + 1}. {obj}" for i, obj in enumerate(env_objects)]
        print(f"Could you help me pick the actual object? {task_name}: {', '.join(numbered_env_objects)}")
        print("Enter the numbers of the correct objects separated by commas (e.g., 1,3 if the first and third are correct):")
        selections = input()
        selected_indices = [int(x.strip()) - 1 for x in selections.split(',') if x.strip().isdigit()]

        correct_args = [env_objects[i] for i in selected_indices
                        if env_objects[i] in task_args]
        return correct_args

    def gen_confirmation(self, user_task: str, task_name: str, task_args: List[str]) -> bool:   
        if self.disable_gen_confirmation:
            return True
        formatted_args = ', '.join(task_args)
        while True:
            user_msg = f"{user_task} is {task_name}({formatted_args}). Is that right? Please respond yes or no."
            self.send_msg(user_msg)
            users_choice = self.get_instructions()
            users_choice = users_choice.lower().strip()
            if users_choice in ['yes', 'no']:
                break
            err_msg = "Invalid input. Please say yes or no"
            self.send_msg(err_msg)
        return users_choice == 'yes'

    def gen_correction(self, task_name: str, task_args: List[str],
                       env_objects: List[str]) -> List[str]: #TODO Figure out how to fix this for speech to text user interface
        numbered_env_objects = [f"{i + 1}. {obj}" for i, obj in enumerate(env_objects)]
        print(f"Could you help me pick the actual object? {task_name}: {', '.join(numbered_env_objects)}")
        print("Enter the numbers of the correct objects separated by commas (e.g., 1,3 if the first and third are correct):")
        selections = input()
        selected_indices = [int(x.strip()) - 1 for x in selections.split(',') if x.strip().isdigit()]

        correct_args = [env_objects[i] for i in selected_indices
                        if env_objects[i] in task_args]
        return correct_args

    def confirm_task_decomposition(self, user_task: str, user_subtasks: List[str]) -> bool:    
        if self.disable_confirm_task_decomposition:
            return True
        while True:
            user_msg = f"Should I decompose { user_task } to { user_subtasks }? Please respond yes or no."
            self.send_msg(user_msg)
            users_choice = self.get_instructions()
            users_choice = users_choice.lower().strip()
            if users_choice in ['yes', 'no']:
                break
            err_msg = "Invalid input. Please say yes or no"
            self.send_msg(err_msg)
        return users_choice == 'yes'

    def confirm_task_execution(self, user_task: str) -> bool: 
        if self.disable_confirm_task_execution:
            return True
        while True:
            user_msg = f"Should I execute { user_task }? Please respond yes or no."
            self.send_msg(user_msg)
            users_choice = self.get_instructions()
            users_choice = users_choice.lower().strip()
            if users_choice in ['yes', 'no']:
                break
            err_msg = "Invalid input. Please say yes or no"
            self.send_msg(err_msg)
        return users_choice == 'yes'

    def display_known_tasks(self, tasks: List[str]):
        print("Known tasks:")
        for i, task in enumerate(tasks):
            print(f"({i}): {task}")

if __name__ == "__main__":
    task_manager = ConsoleUserInterface(disable_segment_confirmation=True)
    result_segment_disabled = task_manager.segment_confirmation("a,b,c")
    print(f"Segment confirmation result with disable: {result_segment_disabled}")
    task_name = "place"
    task_args = ["", "pot", "spoon"]
    env_objects = ["X", "O"]
    

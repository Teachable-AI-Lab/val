from typing import List
from typing import Optional

from val.utils import Task
from val.user_interfaces.abstract_interface import AbstractUserInterface


class ConsoleUserInterface(AbstractUserInterface):
    
    def __init__(self, disable_segment_confirmation: bool = False, disable_map_confirmation: bool = False,
                 disable_map_correction: bool = False, disable_map_new_method_confirmation: bool = False, 
                 disable_ground_confirmation: bool = False, disable_ground_correction: bool = False,
                 disable_gen_confirmation: bool = False, disable_gen_correction: bool = False,
                 disable_confirm_task_decomposition: bool = False, disable_confirm_task_execution: bool = False, 
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
               
    def request_user_task(self) -> str:
        user_task = input(f"How can I help you today? ")
        return user_task

    def ask_subtasks(self, user_task: str) -> str:
        steps = input(f"What are the steps for completing the task '{user_task}'? ")
        return steps

    def ask_rephrase(self, user_tasks: str) -> str:
        # TODO ask step by step or rephrase as a whole? should we
        # include options: "add more steps/yes/no"?
        rephrased_user_tasks = input(
                f"Sorry about that. Can you rephrase the tasks '{user_tasks}'?")
        return rephrased_user_tasks

    def segment_confirmation(self, steps: List[str]) -> bool:
        if self.disable_segment_confirmation:
            return True   
        print("These are the individual steps of your command, right?")
        [print(index,step) for index, step in enumerate(steps, start=1)]
        while True:
            users_choice = input("Please enter 'y' or 'n': ").strip().lower()
            if users_choice in ['y', 'n']:
                break
            print("Invalid input. Please enter 'y' or 'n'.")
        return users_choice == 'y'

    def map_confirmation(self, user_task: str, task_name: str) -> bool:
        if self.disable_map_confirmation:
            return True 
        print(f"I think that '{user_task}' is the action '{task_name}'. Is that right?")
        while True:
            users_choice = input("Please enter 'y' or 'n': ").strip().lower()
            if users_choice in ['y', 'n']:
                break
            print("Invalid input. Please enter 'y' or 'n'.")
        return users_choice == 'y'

    def map_correction(self, user_task: str, known_tasks: List[str]) -> Optional[int]:
        print(f"Which of these is the best choice for '{user_task}'?")
        for i, task in enumerate(known_tasks):
            print(f"({chr(ord('a')+i)}): {task}")

        choices=[chr(ord('a')+i) for i in range(len(known_tasks))]
        while True:
            users_choice = input(f"Please enter {choices}:")
            if users_choice.lower() in choices:
                break
            print(f"Invalid input. Please enter {choices}:")
        users_choice_int=ord(users_choice)-ord('a')
        return users_choice_int if users_choice_int < len(known_tasks) else None

    def map_new_method_confirmation(self, user_task: str) -> bool:
        if self.disable_map_new_method_confirmation:
            return True
        print(f"The task '{user_task}' is a new method. Is that right?")
        while True:
            users_choice = input("Please enter 'y' or 'n': ").strip().lower()
            if users_choice in ['y', 'n']:
                break
            print("Invalid input. Please enter 'y' or 'n'.")
        return users_choice == 'y'

    def ground_confirmation(self, task_name: str, task_args: List[str]) -> bool:       
        if self.disable_ground_confirmation:
            return True 
        formatted_args = ', '.join(task_args)
        print(f"The task is {task_name}({formatted_args}). Is that right?")
        while True:
            users_choice = input("Please enter 'y' or 'n': ").strip().lower()
            if users_choice in ['y', 'n']:
                break
            print("Invalid input. Please enter 'y' or 'n'.")
        return users_choice == 'y'

    def ground_correction(self, task_name: str, task_args: List[str],
                          env_objects: List[str]) -> List[str]:
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
        print(f"{user_task} is {task_name}({formatted_args}). Is that right?")
        while True:
            users_choice = input("Please enter 'y' or 'n': ").strip().lower()
            if users_choice in ['y', 'n']:
                break
            print("Invalid input. Please enter 'y' or 'n'.")
        return users_choice == 'y'

    def gen_correction(self, task_name: str, task_args: List[str],
                       env_objects: List[str]) -> List[str]:
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
        print(f"Should I decompose { user_task } to { user_subtasks }?")
        while True:
            users_choice = input("Please enter 'y' or 'n': ").strip().lower()
            if users_choice in ['y', 'n']:
                break
            print("Invalid input. Please enter 'y' or 'n'.")
        return users_choice == 'y'

    def confirm_task_execution(self, user_task: str) -> bool: 
        if self.disable_confirm_task_execution:
            return True
        print(f"Should I execute { user_task }?")
        while True:
            users_choice = input("Please enter 'y' or 'n': ").strip().lower()
            if users_choice in ['y', 'n']:
                break
            print("Invalid input. Please enter 'y' or 'n'.")
        return users_choice == 'y'

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
    

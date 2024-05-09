from val.user_interfaces.abstract_interface import AbstractUserInterface
from typing import List, Optional


class ConsoleUserInterface(AbstractUserInterface):

    def __init__(self):
        pass

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
        print("These are the individual steps of your command, right?")
        [print(index,step) for index, step in enumerate(steps, start=1)]
        while True:
            users_choice = input("Please enter 'Yes' or 'No':")
            if users_choice.lower() in ['yes', 'no']:
                break
            print("Invalid input. Please enter 'Yes' or 'No'.")
        return True if users_choice.lower()=='yes' else False

    def map_confirmation(self, user_task: str, task_name: str) -> bool:
        print(f"I think that '{user_task}' is the action '{task_name}'. Is that right?")
        while True:
            users_choice = input("Please enter 'Yes' or 'No':")
            if users_choice.lower() in ['yes', 'no']:
                break
            print("Invalid input. Please enter 'Yes' or 'No'.")
        return True if users_choice.lower()=='yes' else False

    def map_correction(self, user_task: str, known_tasks: List[str]) -> Optional[int]:
        print(f"Which of these is the best choice for '{user_task}'?")
        [print(task) for i, task in enumerate(known_tasks)]
        choices=[chr(ord('a')+i) for i in range(len(known_tasks))]
        while True:
            users_choice = input(f"Please enter {choices}:")
            if users_choice.lower() in choices:
                break
            print(f"Invalid input. Please enter {choices}:")
        users_choice_int=ord(users_choice)-ord('a')
        return users_choice_int+1 if users_choice_int < len(known_tasks)-1 else None

    def map_new_method_confirmation(self, user_task: str) -> bool:
        print(f"The task '{user_task}' is a new method. Is that right?")
        while True:
            users_choice = input("Please enter 'Yes' or 'No':")
            if users_choice.lower() in ['yes', 'no']:
                break
            print("Invalid input. Please enter 'Yes' or 'No'.")
        return True if users_choice.lower()=='yes' else False

    def ground_confirmation(self, task_name: str, task_args: List[str]) -> bool:
        formatted_args = ', '.join(task_args)
        print(f"The task is {task_name}({formatted_args}). Is that right?")
        while True:
            users_choice = input("Please enter 'Yes' or 'No':")
            if users_choice.lower() in ['yes', 'no']:
                break
            print("Invalid input. Please enter 'Yes' or 'No'.")
        return True if users_choice.lower()=='yes' else False

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
        formatted_args = ', '.join(task_args)
        print(f"{user_task} is {task_name}({formatted_args}). Is that right?")
        while True:
            users_choice = input("Please enter 'Yes' or 'No':")
            if users_choice.lower() in ['yes', 'no']:
                break
            print("Invalid input. Please enter 'Yes' or 'No'.")
        return True if users_choice.lower()=='yes' else False

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

if __name__ == "__main__":
    task_manager = ConsoleUserInterface()
    task_name = "place"
    task_args = ["", "pot", "spoon"]
    env_objects = ["X", "O"]
    #####Test######
    steps = task_manager.ask_subtasks(task_name)
    print("Steps to complete the task:", steps)
    #corrected_args = task_manager.ground_correction(task_name, task_args, env_objects)
    #print("Corrected Arguments:", corrected_args)

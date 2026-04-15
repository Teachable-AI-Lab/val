from typing import List
from typing import Optional

from val.utils import Task


class AbstractUserInterface:
    ### new functions for GUI ###
    def check_for_break(self) -> bool:
        """
        Check if the user wants to break.
        """
        raise NotImplementedError("Not implemented yet")
    
    # def select_task_decomposition(self, task: Task, subtasks: List[Task]) -> bool:
    #     """
    #     Takes a user_task and the user_subtasks it decomposes into and asks the
    #     user if this is the right thing to do, returns bool.
    #     """
    #     raise NotImplementedError("Not implemented yet")

    def query_next_decomposition_and_rewards(self):
        raise NotImplementedError("Not implemented yet")        

    def query_next_decomposition_with_edit(self, task_exec, method_execs):
        """
        Enhanced version that allows users to edit decomposition options
        Supports two edit modes:
        1. GUI edit: User edits directly in the interface
        2. Chatbot edit: User responds via chatbot (triggers query_new_method_exec)
        Returns (chosen_or_edited_method_exec, rewards)
        """
        raise NotImplementedError("Not implemented yet")

    def handle_edited_decomposition(self, task_exec, edited_decomposition):
        """
        Handle user-edited decomposition and convert it to a new MethodEx
        Args:
            task_exec: The task being decomposed
            edited_decomposition: Dictionary containing the edited decomposition from frontend
        Returns:
            MethodEx: The new method execution created from the edited decomposition
        """
        raise NotImplementedError("Not implemented yet")

    def display_added_method(self, task: Task, subtasks: List[Task]) -> None:
        """
        Takes a user_task and the user_subtasks. No return value, just displays.
        """
        raise NotImplementedError("Not implemented yet")

    def correct_grounding(self, user_task: str, task_name: str, task_args: List[str], env_objects: List[str], available_actions: List[str]) -> tuple[str, List[str]]:
        """
        Allow user to correct the grounding result (action and objects)
        Returns (corrected_task_name, corrected_task_args)
        """
        raise NotImplementedError("Not implemented yet")
   
    def confirm_task_execution(self, user_task: str) -> bool:
        """
        Takes a user_task and asks the user if this is the right thing to
        execute, returns bool.
        """
        raise NotImplementedError("Not implemented yet")

    def display_known_tasks(self, tasks: List[str]):
        """
        Display the known tasks to the user.
        """
        raise NotImplementedError("Not implemented yet")

    def display_explanation(self, explanation: str) -> None:
        """
        Display the AI agent's decision explanation to the user.
        """
        raise NotImplementedError("Not implemented yet")

    def update_graph_vis(self, root_task_exec):
        pass

    ### old functions for chat ###
    def request_user_task(self) -> str:
        """
        Initial prompt to request a task from the user.
        """
        raise NotImplementedError("Not implemented yet")

    def ask_subtasks(self, user_task: str, task_exec=None) -> str:
        """
        Takes a user task, asks how to do it, returns response.
        """
        raise NotImplementedError("Not implemented yet")

    def ask_rephrase(self, user_tasks: str) -> str:
        """
        Takes user tasks (potentially many) and asks the user to rephrase.
        """
        raise NotImplementedError("Not implemented yet")

    def segment_confirmation(self, steps: List[str]) -> bool:
        """
        Presents a list of the steps and asks if they are correct.
        """
        raise NotImplementedError("Not implemented yet")

    def map_confirmation(self, user_task: str, task_name: str) -> bool:
        """
        Takes a user task and the resolved task name and asks if it is right.
        """
        raise NotImplementedError("Not implemented yet")

    def map_correction(self, user_task: str, known_tasks: List[str]) -> Optional[int]:
        """
        Takes a user task and the known tasks it might map to and returns the
        index of the user specified task or None, if none of them.
        """
        raise NotImplementedError("Not implemented yet")

    def map_new_method_confirmation(self, user_task: str) -> bool:
        """
        Takes the user task and asks if it should actually be a new method.
        """
        raise NotImplementedError("Not implemented yet")

    def ground_confirmation(self, task_name: str, task_args: List[str]) -> bool:
        """
        Takes the task name and args and ask if they are right
        """
        raise NotImplementedError("Not implemented yet")

    def ground_correction(self, task_name: str, task_args: List[str],
                          env_objects: List[str]) -> List[str]: 
        """
        Takes the task name and the predicted args and the env_objects and
        asks the user to correct the arg objects.

        Should return new list of task args that are correct.
        """
        raise NotImplementedError("Not implemented yet")

    def gen_confirmation(self, user_task: str, task_name: str, task_args: List[str]) -> bool:
        """
        Takes the task_name, and args and ask if the args are correct given the user_task.
        """
        raise NotImplementedError("Not implemented yet")

    def gen_correction(self, task_name: str, task_args: List[str],
                       env_objects: List[str]) -> List[str]:
        """
        Takes the task name and the predicted args and the env_objects and
        asks the user to correct the args.

        Should return new list of task args that are correct.
        """
        raise NotImplementedError("Not implemented yet")
    




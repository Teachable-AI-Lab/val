from typing import List
from typing import Optional


class AbstractUserInterface:

    def __init__(self):
        pass

    def ask_subtasks(self, user_task: str) -> str:
        """
        Tasks a user task, asks how to do it, returns response.
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

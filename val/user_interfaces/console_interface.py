from typing import List, Sequence, Optional, Tuple

from val.utils import Task
from val.user_interfaces.abstract_interface import AbstractUserInterface
from val.utils import normalize_grounding_args
from pyhtn.htn import Task, Method, Operator, TaskEx, MethodEx, OperatorEx, tree_dict_to_str


class ConsoleUserInterface(AbstractUserInterface):
    
    def __init__(self, disable_segment_confirmation: bool = False, disable_map_confirmation: bool = False,
                 disable_map_correction: bool = False, disable_map_new_method_confirmation: bool = False, 
                 disable_ground_confirmation: bool = False, disable_ground_correction: bool = False,
                 disable_gen_confirmation: bool = False, disable_gen_correction: bool = False,
                 disable_confirm_task_decomposition: bool = False, disable_confirm_task_execution: bool = False, 
                 next_select_kind = "one at a time"

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
            print(f"Should I decompose { task_exec.fn_str() } to { subtasks_str }?")
            users_choice = input("Please enter 'y' or 'n': ").strip().lower()
            if users_choice in ['y', 'n']:
                break
            print("Invalid input. Please enter 'y' or 'n'.")
        return users_choice == 'y'

    def _select_task_decomposition(self, task_exec, method_execs):
        print(f"\nMain Task: {task_exec}\n")
        print("Choose a task decomposition method:")

        for i, method_exec in enumerate(method_execs):
            subtask_execs =  method_exec.subtask_execs
            option = chr(ord('a') + i)
            print(f"  {option}) {subtask_execs}")
            
        print("\nEnter the letter of the decomposition to select it (e.g., a, b, c), or type 'NA' to skip:")
        while True:
            user_input = input("Your choice: ").strip().lower()
            if user_input == 'na':
                return None
            elif len(user_input) == 1 and 'a' <= user_input <= chr(ord('a') + len(subtask_execs) - 1):
                return ord(user_input) - ord('a')
            else:
                print("Invalid input. Please enter a valid option (a, b, ...) or 'NA'.")

    
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

    def query_next_decomposition_with_edit(self, 
        task_exec: TaskEx, 
        method_execs: Sequence[MethodEx],
        available_actions: Optional[List[str]] = None,
        env_objects: Optional[List[str]] = None,
        decision_explanation: Optional[str] = None) -> Tuple[MethodEx, Sequence[Optional[float]]]:
        """
        Enhanced version that allows users to edit decomposition options
        Supports GUI edit: user edits directly in the interface.
        Returns (chosen_or_edited_method_exec, rewards)
        """
        if(method_execs is None or len(method_execs) == 0):
            print(f"No decomposition methods available for task: {task_exec}")
            print("Would you like to create a new decomposition method? (y/n)")
            while True:
                choice = input().strip().lower()
                if choice in ['y', 'n']:
                    break
                print("Invalid input. Please enter 'y' or 'n'.")
            
            if choice == 'y':
                print("Please describe the new decomposition method:")
                new_method_description = input().strip()
                # Store for later processing
                self.last_edited_decomposition = {'description': new_method_description}
                return None, []
            else:
                return None, []
        else:
            if decision_explanation:
                print(f"\n{decision_explanation}")
                
            print(f"\nTask: {task_exec}")
            print("Available decomposition methods:")
            
            for i, method_exec in enumerate(method_execs):
                subtask_execs = method_exec.subtask_execs
                print(f"  {i+1}) {subtask_execs}")
            
            print("\nOptions:")
            print("  - Enter a number to select a method")
            print("  - Enter 'edit' to modify an existing method")
            print("  - Enter 'new' to create a new method")
            print("  - Enter 'skip' to skip")
            
            while True:
                choice = input("Your choice: ").strip().lower()
                
                if choice == 'skip':
                    return None, []
                elif choice == 'new':
                    print("Please describe the new decomposition method:")
                    new_method_description = input().strip()
                    self.last_edited_decomposition = {'description': new_method_description}
                    return None, []
                elif choice == 'edit':
                    print("Which method would you like to edit? (enter number):")
                    try:
                        method_index = int(input().strip()) - 1
                        if 0 <= method_index < len(method_execs):
                            print("Please describe the edited decomposition method:")
                            edited_description = input().strip()
                            self.last_edited_decomposition = {
                                'original_method': method_execs[method_index],
                                'description': edited_description
                            }
                            return None, []
                        else:
                            print("Invalid method number.")
                    except ValueError:
                        print("Invalid input. Please enter a number.")
                else:
                    try:
                        method_index = int(choice) - 1
                        if 0 <= method_index < len(method_execs):
                            rewards = [None] * len(method_execs)
                            rewards[method_index] = 1.0
                            return method_execs[method_index], rewards
                        else:
                            print("Invalid method number.")
                    except ValueError:
                        print("Invalid input. Please enter a valid option.")

    def handle_edited_decomposition(self, task_exec: TaskEx, edited_decomposition: dict) -> MethodEx:
        """
        Handle user-edited decomposition and convert it to a new MethodEx
        Args:
            task_exec: The task being decomposed
            edited_decomposition: Dictionary containing the edited decomposition from frontend
        Returns:
            MethodEx: The new method execution created from the edited decomposition
        """
        print(f"Processing edited decomposition for task: {task_exec}")
        print(f"Edited decomposition: {edited_decomposition}")
        
        # For console interface, we'll create a simple MethodEx
        # In a real implementation, you would parse the edited_decomposition
        # and create a proper MethodEx object
        
        # This is a placeholder implementation
        # You would need to implement proper parsing and MethodEx creation
        print("Note: Console interface does not support full MethodEx creation from edited decomposition.")
        print("This functionality is primarily designed for web interface.")
        
        # Return a placeholder MethodEx (this would need proper implementation)
        return None
        
    def display_added_method(self, task_exec: TaskEx, method_exec: MethodEx) -> None: 
        print("Added Decomposition Method:")
        print(f"Main Task: {task_exec.task.name}")
        print("Subtasks:")
        for i, subtask in enumerate(method_exec.method.subtasks, start=1):
            print(f"  {i}. {subtask.name}")

               
    def request_user_task(self) -> str:
        user_task = input(f"How can I help you today? ")
        return user_task

    def ask_subtasks(self, user_task: str, task_exec=None) -> str:
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
        question_text = (
            "This is the step of your command, right?"
            if len(steps) == 1
            else "These are the individual steps of your command, right?"
        )
        print(question_text)
        for index, step in enumerate(steps, start=1):
            print(f"{index}. {step}")
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

    def correct_grounding(self, user_task: str, task_name: str, task_args: List[str], env_objects: List[str], available_actions: List[str]) -> tuple[str, List[str]]:
        """
        Allow user to correct the grounding result (action and objects)
        Returns (corrected_task_name, corrected_task_args)
        """
        print(f"Correct the grounding for: '{user_task}'")
        print(f"Current action: {task_name}")
        print(f"Current objects: {', '.join(task_args)}")
        print(f"Available objects: {', '.join(env_objects)}")
        print(f"Available actions: {', '.join(available_actions)}")
        print("Enter the corrected action and objects in format 'action:object1,object2' (or press Enter to keep current):")
        
        response = input().strip()
        if ':' in response:
            corrected_task_name, objects_str = response.split(':', 1)
            corrected_task_args = [obj.strip() for obj in objects_str.split(',') if obj.strip()]
        else:
            corrected_task_name = task_name
            corrected_task_args = task_args
        corrected_task_args = normalize_grounding_args(corrected_task_name, corrected_task_args)
            
        return corrected_task_name, corrected_task_args

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

    def display_explanation(self, explanation: str) -> None:
        """
        Display the AI agent's decision explanation to the user.
        """
        print("\n" + "="*60)
        print("🤖 AI DECISION EXPLANATION")
        print("="*60)
        
        # Check if explanation already contains formatted sections
        if "Task:" in explanation and "Available methods:" in explanation:
            # If it's already formatted, just print it as is
            print(explanation)
        else:
            # If it's not formatted, add some basic formatting
            print(f"Explanation: {explanation}")
        
        print("="*60 + "\n")

if __name__ == "__main__":
    task_manager = ConsoleUserInterface(disable_segment_confirmation=True)
    result_segment_disabled = task_manager.segment_confirmation("a,b,c")
    print(f"Segment confirmation result with disable: {result_segment_disabled}")
    task_name = "place"
    task_args = ["", "pot", "spoon"]
    env_objects = ["X", "O"]
    

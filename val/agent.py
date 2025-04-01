from typing import List
from typing import Optional

from val.utils import load_prompt
from val.utils import task_to_gpt_str
from shop2.domain import Task
from shop2.common import V
from val.gpt_completer import GPTCompleter
from val.user_interfaces.abstract_interface import AbstractUserInterface
from val.env_interfaces.abstract_interface import AbstractEnvInterface
from val.htn_interfaces.abstract_interface import AbstractHtnInterface


class ValAgent:

    def __init__(self,
                 env: AbstractEnvInterface,
                 user_interface_class,
                 htn_interface_class,
                 openai_key: str):

        self.segment_prompt = load_prompt("prompts/chat_segmenter.txt")
        self.name_prompt = load_prompt('prompts/chat_namer.txt')
        self.gen_prompt = load_prompt('prompts/chat_gen.txt')
        self.para_prompt = load_prompt('prompts/chat_paraphrase_ider.txt')
        self.verb_prompt = load_prompt('prompts/chat_verbalizer.txt')
        self.map_prompt = load_prompt('prompts/chat_map.txt')
        self.ground_prompt = load_prompt('prompts/chat_ground.txt')

        self.gpt = GPTCompleter(openai_key)

        self.user_interface = user_interface_class()
        self.env = env
        self.htn_interface = htn_interface_class(self)

    def start(self):
        while True:

            # Get current task node from planner and pass this to the user interface

            tasks = [self.verbalize_gpt(t, [arg.name for arg in t.args])
                                        for t, _ in self.htn_interface.get_tasks()]
            self.user_interface.display_known_tasks(tasks)

            user_tasks = self.user_interface.request_user_task()
            tasks = [task for task in self.interpret(user_tasks)]
            planner = self.htn_interface.get_planner(tasks)

            user_choice = None

            try:
                while True:
                    if self.user_interface.check_for_break():
                        break

                    task, method_application = planner.get_next_method_application()
                    if method_application is None:
                        method_application = self.add_method_from_task(task)
                        self.user_interface.display_added_method(task, method_application.subtasks)
                        planner.apply(task, method_application)
                        # planner.apply(method, task, subtasks)
                        continue

                    user_choice = self.user_interface.select_task_decomposition(task, method_application.subtasks)

                    if user_choice is None:
                        method_application = self.add_method_from_task(task)
                        self.user_interface.display_added_method(task, method_application.subtasks)
                        planner.apply(task, method_application)
                    else:
                        method = method_application.method
                        method.cond_lrn.ifit(method_application, user_choice)
                        if user_choice:
                            planner.apply(task, method_application)
                        #else:
                        #    planner.mark_incorrect(method, task, subtasks)

            except FailedPlanException:
                # Signify Failure
                pass

    def interpret(self, user_tasks: str) -> List[Task]:
        """
        Takes a string of natural language from the user and returns a list of Tasks
        """
        segmented_tasks = self.segment_gpt(user_tasks)
        while not self.user_interface.segment_confirmation(segmented_tasks):
            # TODO consider adding/editing steps here.
            user_tasks = self.user_interface.ask_rephrase(user_tasks)
            segmented_tasks = self.segment_gpt(user_tasks)

        for user_task in segmented_tasks:
            task_ungrounded = self.map_gpt(user_task)

            if ((task_ungrounded is None and
                   not self.user_interface.map_new_method_confirmation(user_task)) or
                  (task_ungrounded is not None and
                   not self.user_interface.map_confirmation(user_task, task_ungrounded.name))):
                # TODO add to htn interface
                # TODO consider how we convert tasks to strings and handle args
                known_tasks = [t for t, _ in self.htn_interface.get_tasks()]
                # known_tasks = self.htn_interface.get_tasks()
                str_known_tasks = [task_to_gpt_str(task, "") for task in known_tasks]
                user_correction_index = self.user_interface.map_correction(user_task, str_known_tasks)
                if user_correction_index is None:
                    task_ungrounded = None
                else:
                    task_ungrounded = known_tasks[int(user_correction_index)]

            if task_ungrounded is None:
                task_name = self.name_gpt(user_task)
                task_args = self.gen_gpt(user_task, task_name)
                if not self.user_interface.gen_confirmation(user_task, task_name, task_args):
                    task_args = self.user_interface.gen_correction(task_name, task_args,
                                                           self.env.get_objects())
                yield Task(task_name, task_args)

            else:
                task_args = self.ground_gpt(user_task, task_ungrounded)
                if not self.user_interface.ground_confirmation(task_ungrounded.name, task_args):
                    task_args = self.user_interface.ground_correction(task_ungrounded.name,
                                                                      task_args,
                                                                      self.env.get_objects())

                verbalized_task = self.verbalize_gpt(task_ungrounded, task_args)

                if (self.paraphrase_gpt(verbalized_task, user_task) or
                     self.user_interface.gen_confirmation(user_task, task_ungrounded.name, task_args)):
                    yield Task(task_ungrounded.name, *task_args)
                else:
                    for subtask in self.add_method_from_user_task(user_task):
                        yield subtask

    def add_method_from_task(self, task: Task):
        """
        Returns an HTN method
        """
        verbalized_task = self.verbalize_gpt(task, task.args)
        user_subtasks = self.user_interface.ask_subtasks(verbalized_task)
        subtasks = []
        for subtask in self.interpret(user_subtasks):
            yield subtask
            subtasks.append(subtask)

        # TODO maybe consider a gpt module that names these better...
        arg_map = {arg: V(chr(ord('A')+i))
                   for i, arg in enumerate(task.args)}

        task_args_v = [arg_map[arg] for arg in task.args]
        subtasks_v = [Task(subtask.name,
                         *[arg_map[subarg] if subarg in arg_map else subarg
                                for subarg in subtask.args])
                    for subtask in subtasks]

        preconditions = []
        return self.htn_interface.add_method(task.name, task_args_v, preconditions, subtasks_v)

    def segment_gpt(self, user_tasks: str) -> List[str]:
        # SEGMENTS: 1. "cook an onion" (resolved pronouns: "cook an onion")
        resp = self.gpt.get_chat_gpt_completion(f'{self.segment_prompt}"{user_tasks}"')
        segmented_user_tasks = []
        for line in resp.split('\n'):
            # Code parses string '2. "interact with it" (resolved pronouns: "interact with the onion")'
            # to get "interact with the onion" out.
            segmented_user_tasks.append(line.split('"')[3])

        return segmented_user_tasks

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


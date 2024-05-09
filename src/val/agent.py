from val.utils import load_prompt
from val.utils import task_to_gpt_str
from val.gpt_completer import GPTCompleter
from val.user_interfaces import AbstractUserInterface
from val.env_interfaces import AbstractEnvInterface
from val.htn_interfaces import AbstractHtnInterface
from dataclasses import dataclass, field
from typing import Any, Tuple, Union

variable_counter = 0

def gen_variable():
    global variable_counter
    variable_counter += 1
    return V(f'genvar{variable_counter}')

@dataclass(eq=False)  e
class V:
    """
    A variable for pattern matching.
    """
    name: str

    def __repr__(self):
        return f"V({self.name})"

    def __hash__(self):
        return hash(f"V({self.name})")

    def __eq__(self, other):
        if not isinstance(other, V):
            return False
        return self.name == other.name

@dataclass
class Task:
    name: str  
    args: Tuple[Union[V, str], ...] = field(default_factory=tuple)
    head: Tuple[str, Union[V, str], ...] = field(init=False)

    def __post_init__(self):
        self.head = (self.name, *self.args)

    def __str__(self):
        return f"Task(name='{self.name}', args={self.args})"
      
      

class ValAgent:

    def __init__(self,
                 user_interface: AbstractUserInterface,
                 env_interface: AbstractEnvInterface,
                 htn_interface: AbstractHtnInterface,
                 openai_key: str):
        self.user_interface = user_interface
        self.env_interface = env_interface

        self.segment_prompt = load_prompt("prompts/chat_segmenter.txt")
        self.name_prompt = load_prompt('prompts/chat_namer.txt')
        self.gen_prompt = load_prompt('prompts/chat_gen.txt')
        self.para_prompt = load_prompt('prompts/chat_paraphrase_ider.txt')
        self.verb_prompt = load_prompt('prompts/chat_verbalizer.txt')
        self.map_prompt = load_prompt('prompts/chat_map.txt')
        self.ground_prompt = load_prompt('prompts/chat_ground.txt')

        self.gpt = GPTCompleter(openai_key)

        self.htn_interface = htn_interface

    def interpret(self, user_tasks: str, htn_knowledge: dict):
        tasks = []

        segmented_tasks = self.segment_gpt(user_tasks)
        while not self.user_interface.segment_confirmation(segmented_tasks):
            # TODO consider adding/editing steps here.
            user_tasks = self.user_interface.ask_rephrase(user_tasks)
            segmented_tasks = self.segment_gpt(user_tasks)

        for user_task in segmented_tasks:
            task_ungrounded = self.map_gpt(user_task)

            if ((task_ungrounded is None and
                   not self.user_interface.map_new_method_confirmation(user_task)) or
                  not self.user_interface.map_confirmation(user_task, task_ungrounded[0])):
                # TODO add to htn interface
                # TODO consider how we convert tasks to strings and handle args
                known_tasks = [task_to_gpt_str(task) for task in self.htn_interface.get_tasks()]
                task_ungrounded = self.user_interface.map_correction(user_task, known_tasks)

            if task_ungrounded is None:
                tasks.append(self.add_method(user_task))

            else:
                task_args = self.ground_gpt(user_task, task_ungrounded)
                if not self.user_interface.ground_confirmation(task_ungrounded[0], task_args):
                    task_args = self.user_interface.ground_correction(task_ungrounded[0],
                                                                      task_args,
                                                                      self.env_interface.get_objects())

                verbalized_task = self.verbalize_gpt(task_ungrounded, task_args)

                if (self.paraphrase_gpt(verbalized_task, user_task) or
                     self.user_interface.gen_confirmation(user_task, task_ungrounded[0], task_args)):
                    # TODO tasks should have indexed access to head tuple
                    # TODO htn_interface.execute_task need implemented and needs env
                    # TODO make sure we handle success correctly
                    tasks.append(Task(task_ungrounded[0], *task_args))
                    success = self.htn_interface.execute_task(tasks[-1])
                    
                    if not success:
                        tasks.append(self.add_method(user_task))
                else:
                    tasks.append(self.add_method(user_task))

        return tasks

    def add_method(self, user_task: str) -> Task:
        """
        Creates a new HTN method and adds it to self.htn_knowledge.
        Returns a task name with args that will match the added method.

        This is only called if the HTN method does not already exist.
        """
        task_name = self.name_gpt(user_task)
        user_subtasks = self.user_interface.ask_subtasks(user_task)
        subtasks = self.interpret(user_subtasks)
        task_args = self.gen_gpt(user_task, task_name, subtasks)
        if not self.user_interface.gen_confirmation(user_task, task_name, task_args):
            task_args = self.user_interface.gen_correction(task_name, task_args,
                                                           self.env_interface.get_objects())


        # TODO maybe consider a gpt module that names these better...
        arg_map = {arg: V(chr(ord('A')+i))
                   for i, arg in enumerate(task_args)}

        task_args = [arg_map[arg] for arg in task_args]
        subtasks = [Task(task[0], *[arg_map[subarg] if subarg in arg_map else subarg
                                    for subarg in task[1:]])
                    for task in subtasks]

        self.htn_interface.add_method(task_name, task_args, subtasks)
        return Task(task_name, *task_args)

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
        tasks = self.htn_interface.get_tasks()

        task_list = [f"[{chr(ord('a')+i)}] {task_to_gpt_str(task)}"
                     for i, task in enumerate(tasks)]

        # TODO get_objects returns -> ['onion', 'pot', ...]
        object_list = self.env_interface.get_objects()
		name_list = [x.split('(')[0] for x in task_list]
		name_list.append(f"[{chr(ord('a')+len(known_actions)}] None of the above; "
                         f'"{user_task}" would require a combination of actions.')

		task_str = ', '.join(task_list)
		object_str = ', '.join(object_list)
		name_str = '\n'.join(name_list)

        prompt = self.map_prompt % (task_str, object_str,
                                             user_task, name_str)
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
		num_args = len(task_ungrounded) - 1
        if num_args == 0:
		    return task_ungrounded

        object_list = self.env_interface.get_objects()
		object_str = ', '.join(object_list)

		num_args_str = '%d argument%s' % (num_args, '' if num_args==1 else 's')
		num_objs_str = '%d object%s' % (num_args, '' if num_args==1 else 's')

		task_name = task[0] 

		o_list = ', '.join([('o%d' % (i+1)) for i in range(num_args)])

		prompt = self.ground_prompt % (task_to_gpt_str(task_ungrounded), user_task, obj_str, task_name, num_args_str, num_objs_str, task_name, o_list)

		resp = self.gpt.get_chat_gpt_completion(prompt).strip()

		if '"' in resp:
			resp = resp.replace('"', '').strip()
        
        resp = resp.replace(" ", "")
        resp = resp.split("(")[1]
        resp = resp.split(")")[0]
        resp = resp.split(",")

		return resp

    def gen_gpt(self, user_task: str, task_name: str, subtasks: List[Task]) -> List[str]:

        objects = set(arg for task in subtasks for arg in task[1:])
        
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
        task = f"{task_ungrounded[0]}({', '.join(task_args)})"
        return self.gpt.get_chat_gpt_completion(f"{self.verb_prompt}{task}")

    def paraphrase_gpt(self, verbalized_task: str, user_task: str) -> bool:
        """
        Takes a verbalized task (generated from task name and args) and the
        original user_task and returns whether they are the same.
        """
		res = self.gpt.get_chat_gpt_completion(
                self.para_prompt%('"%s" and %s' % (action, pred))).split(" ")
		return res == 'yes'

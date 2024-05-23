import os
import yaml
from dataclasses import dataclass
from dataclasses import field
from typing import Any
from typing import Tuple
from typing import Union
from shop2.domain import Task

# @dataclass(eq=True, frozen=True)
# class V:
#     """
#     A variable for pattern matching.
#     """
#     name: str

#     def to_unify_str(self):
#         return f"?{ self.name }"

# @dataclass(eq=True, frozen=True)
# class Task:
#     name: str
#     args: Tuple[Union[str, V], ...]

#     @property
#     def head(self):
#         return (self.name, *self.args)

def load_prompt(prompt_fn: str) -> str:
    #__file__是Python中内置的变量,它表示当前文件的文件名
    new_fn = os.path.join(os.path.dirname(__file__), prompt_fn)

    try:
        with open(new_fn, 'r') as f:
            return f.read().strip()
    except:
        print('error loading prompt from filename %s' % (new_fn,))
        return None


def task_to_gpt_str(task: Task, description: str) -> str:
    # return f"{task[0]}({",".join([arg.name for arg in task[1:]])})"
    if description != "":
        return f'{task.name}({",".join([arg.name for arg in task.args])}) - {description}'
    else:
        return f'{task.name}({",".join([arg.name for arg in task.args])})'

def get_openai_key() -> str:
    file_path = "keys.yaml"
    key = "open_ai_key"
    if os.path.exists(file_path):
        with open(file_path, 'r') as file:
            data = yaml.safe_load(file)
            # Check if the key exists in the YAML file
            if key in data:
                if data[key] == '<openai key placeholder>':
                    error_msg = f"Key '{key}' in the existing YAML file is a placeholder."
                    print(error_msg)
                return data[key]

            else:
                error_msg = f"Key '{key}' not found in the existing YAML file."
                print(error_msg)
                data[key] = '<openai key placeholder>'
                with open(file_path, 'w') as file:
                    yaml.safe_dump(data, file)
                return '<openai key placeholder>'
    else:
        # Create a new YAML file with a placeholder
        data = {key: '<openai key placeholder>'}
        with open(file_path, 'w') as file:
            yaml.safe_dump(data, file)
        error_msg = f"File not found. Created a new YAML file with a placeholder for '{key}'."
        print(error_msg)


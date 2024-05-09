import os
import yaml
from dataclasses import dataclass
from dataclasses import field
from typing import Any
from typing import Tuple
from typing import Union


@dataclass(eq=False)
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
    args: Tuple[Union[str, V], ...] = field(init=False)
    
    def __init__(self, name: str, *args: Union[str, V]):
        self.name = name
        self.args = args
        self.__post_init__()

    def __post_init__(self):
        self.head = (self.name, *self.args)

def load_prompt(prompt_fn: str) -> str:
    #__file__是Python中内置的变量,它表示当前文件的文件名
    new_fn = os.path.join(os.path.dirname(__file__), prompt_fn)

    try:
        with open(new_fn, 'r') as f:
            return f.read().strip()
    except:
        print('error loading prompt from filename %s' % (new_fn,))
        return None


def task_to_gpt_str(task: Task) -> str:
    # return f"{task[0]}({",".join([arg.name for arg in task[1:]])})"
    return f'{task[0]}({",".join([chr(ord("A")+i) for i in range(len(task[1:]))])})'

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


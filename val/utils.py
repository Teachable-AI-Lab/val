import os

from agent import Task
from agent import V


def load_prompt(self, prompt_fn):
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
    return f"{task[0]}({",".join([chr(ord('A')+i) for i in range(len(task[1:]))])})"


class V:
    pass


class Task:
    pass
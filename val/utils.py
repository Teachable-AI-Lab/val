import os
import yaml
from dataclasses import dataclass
from dataclasses import field
from typing import Any
from typing import Tuple
from typing import Union
from pyhtn.htn import Task


def load_prompt(prompt_fn: str) -> str:
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

def get_openai_config() -> dict:
    """
    Load OpenAI-compatible client config from keys.yaml.

    Supported keys (all optional except api key):
    - open_ai_key / api_key
    - open_ai_base_url / base_url
    - open_ai_model / model
    """
    file_path = "keys.yaml"
    if not os.path.exists(file_path):
        data = {"open_ai_key": "<openai key placeholder>"}
        with open(file_path, "w") as file:
            yaml.safe_dump(data, file)
        print("File not found. Created a new YAML file with a placeholder for 'open_ai_key'.")
        return {"api_key": "<openai key placeholder>", "base_url": None, "model": None}

    with open(file_path, "r") as file:
        data = yaml.safe_load(file) or {}

    api_key = data.get("open_ai_key") or data.get("api_key")
    base_url = data.get("open_ai_base_url") or data.get("base_url")
    model = data.get("open_ai_model") or data.get("model")

    if not api_key:
        print("Key 'open_ai_key' not found in keys.yaml.")
        data["open_ai_key"] = "<openai key placeholder>"
        with open(file_path, "w") as file:
            yaml.safe_dump(data, file)
        api_key = "<openai key placeholder>"

    if api_key == "<openai key placeholder>":
        print("Key 'open_ai_key' in keys.yaml is a placeholder.")

    return {
        "api_key": api_key,
        "base_url": base_url,
        "model": model,
    }


def get_openai_key() -> Union[str, dict]:
    # Backward-compatible API. Existing callers can keep using this function.
    return get_openai_config()


def get_legacy_openai_key() -> str:
    """
    Return only API key string for legacy call sites that need a raw string.
    """
    cfg = get_openai_config()
    return cfg["api_key"]


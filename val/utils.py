import os
import yaml
from dataclasses import dataclass
from dataclasses import field
from typing import Any
from typing import Optional
from typing import TYPE_CHECKING
from typing import List
from typing import Tuple
from typing import Union

if TYPE_CHECKING:
    from pyhtn.htn import Task
else:
    Task = Any


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


def normalize_grounding_args(task_name: str, task_args: List[str]) -> List[str]:
    if task_name.strip().lower() == "act":
        return []
    return task_args

def _default_keys_data() -> dict:
    return {
        "active_profile": "openai",
        "profiles": {
            "openai": {
                "api_key": "<openai key placeholder>",
                "model": "gpt-4",
            }
        }
    }


def _load_keys_yaml(file_path: str) -> dict:
    if not os.path.exists(file_path):
        data = _default_keys_data()
        with open(file_path, "w") as file:
            yaml.safe_dump(data, file, sort_keys=False)
        print("File not found. Created a new YAML file with an 'openai' profile placeholder.")
        return data

    with open(file_path, "r") as file:
        return yaml.safe_load(file) or {}


def _extract_api_settings(data: Optional[dict]) -> dict:
    data = data or {}
    return {
        "api_key": data.get("open_ai_key") or data.get("api_key"),
        "base_url": data.get("open_ai_base_url") or data.get("base_url"),
        "model": data.get("open_ai_model") or data.get("model"),
    }


def _apply_env_overrides(config: dict) -> dict:
    config = dict(config)
    env_api_key = os.getenv("OPENAI_API_KEY")
    env_base_url = os.getenv("OPENAI_BASE_URL")
    env_model = os.getenv("OPENAI_MODEL")

    if env_api_key:
        config["api_key"] = env_api_key
    if env_base_url:
        config["base_url"] = env_base_url
    if env_model:
        config["model"] = env_model

    return config


def get_openai_config(profile_name: Optional[str] = None) -> dict:
    """
    Load OpenAI-compatible client config from keys.yaml.

    Supported formats:
    1. Legacy flat config:
       - open_ai_key / api_key
       - open_ai_base_url / base_url
       - open_ai_model / model
    2. Profile-based config:
       active_profile: lab
       profiles:
         openai:
           api_key: ...
           model: gpt-4
         lab:
           api_key: ...
           base_url: https://...
           model: models/...

    Profile selection order:
    - explicit profile_name argument
    - VAL_API_PROFILE environment variable
    - active_profile from keys.yaml
    - first profile in keys.yaml

    Environment overrides for the selected profile:
    - OPENAI_API_KEY
    - OPENAI_BASE_URL
    - OPENAI_MODEL
    """
    file_path = "keys.yaml"
    data = _load_keys_yaml(file_path)

    selected_profile = profile_name or os.getenv("VAL_API_PROFILE")
    profiles = data.get("profiles") or {}

    if profiles:
        selected_profile = selected_profile or data.get("active_profile")
        if not selected_profile:
            selected_profile = next(iter(profiles))

        if selected_profile not in profiles:
            raise KeyError(f"Profile '{selected_profile}' not found in keys.yaml. Available profiles: {', '.join(profiles.keys())}")

        config = _extract_api_settings(profiles[selected_profile])
        config["profile"] = selected_profile
    else:
        config = _extract_api_settings(data)
        config["profile"] = selected_profile or "default"

    config = _apply_env_overrides(config)

    api_key = config.get("api_key")

    if api_key == "<openai key placeholder>":
        print("Key 'open_ai_key' in keys.yaml is a placeholder.")
    elif not api_key:
        print("No API key configured for the selected profile.")

    return config


def get_openai_key(profile_name: Optional[str] = None) -> Union[str, dict]:
    # Backward-compatible API. Existing callers can keep using this function.
    return get_openai_config(profile_name=profile_name)


def get_legacy_openai_key(profile_name: Optional[str] = None) -> str:
    """
    Return only API key string for legacy call sites that need a raw string.
    """
    cfg = get_openai_config(profile_name=profile_name)
    return cfg["api_key"]


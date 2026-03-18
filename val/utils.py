import os
import yaml
from dataclasses import dataclass
from dataclasses import field
from typing import Any
from typing import Tuple
from typing import Union
from pyhtn.htn import Task

try:
    from dotenv import dotenv_values as _dotenv_values
    def _load_dotenv(path: str) -> dict:
        return dict(_dotenv_values(path))
except ImportError:
    def _load_dotenv(path: str) -> dict:  # type: ignore[misc]
        """Minimal .env parser used when python-dotenv is not installed."""
        result = {}
        if not os.path.exists(path):
            return result
        with open(path) as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith("#") or "=" not in line:
                    continue
                k, _, v = line.partition("=")
                result[k.strip()] = v.strip().strip('"').strip("'")
        return result


_ENV_DEFAULTS = {
    "OPENAI_API_KEY": "<your-api-key>",
    "OPENAI_BASE_URL": "<your-base-url-or-leave-blank-for-openai-default>",
    "OPENAI_MODEL": "<model-name-e.g.-gpt-4o>",
    "MAX_CONTEXT_TOKENS": "<max-context-tokens-e.g.-120000>",
}

_ENV_COMMENTS = {
    "OPENAI_API_KEY": "# OpenAI (or compatible) API credentials",
    "OPENAI_MODEL": "# Model and context settings",
}


def get_env_config(dotenv_path: str = ".env") -> dict:
    """Load configuration from a .env file.

    Creates the file with placeholder values if it does not exist, then
    appends any keys that are present in the defaults but missing from the
    file.  Returns a dict with at minimum:

      OPENAI_API_KEY      – API key for OpenAI (or compatible) endpoint
      OPENAI_BASE_URL     – base URL (empty string → use OpenAI default)
      OPENAI_MODEL        – model name (default: gpt-4o)
      MAX_CONTEXT_TOKENS  – token budget before history trimming (default: 120000)
    """
    cfg = _load_dotenv(dotenv_path)

    # Determine which keys are missing from the file
    missing = {k: v for k, v in _ENV_DEFAULTS.items() if k not in cfg}

    if missing:
        # Append missing keys (with section comments) to the file
        lines = []
        if not os.path.exists(dotenv_path):
            lines.append("# Auto-generated configuration — fill in the placeholders below\n")
        else:
            lines.append("\n# Keys added automatically\n")

        for key, placeholder in missing.items():
            if key in _ENV_COMMENTS:
                lines.append(_ENV_COMMENTS[key] + "\n")
            lines.append(f"{key}={placeholder}\n")

        with open(dotenv_path, "a") as f:
            f.writelines(lines)

        if not os.path.exists(dotenv_path):
            print(f"Created '{dotenv_path}' with placeholder values — please fill them in.")
        else:
            print(f"Added missing keys to '{dotenv_path}' — please fill in the placeholders.")

        cfg.update(missing)

    # Treat placeholder values as absent
    for key in list(cfg):
        val = cfg.get(key, "")
        if isinstance(val, str) and val.startswith("<"):
            cfg[key] = None

    return cfg


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

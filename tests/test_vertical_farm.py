from val.agent import ValAgent
from val.user_interfaces.console_interface import ConsoleUserInterface
from val.user_interfaces.web_interface import WebInterface
from val.env_interfaces.vertical_farm.vertical_farm_env_htn import VerticalFarmHTNEnv
from val.htn_interfaces.basic_htn_interface import BasicHtnInterface
from val.utils import get_openai_key
from val.htn_interfaces.py_htn_interface import PyHtnInterface
import threading
import pygame
import asyncio


if __name__ == "__main__":
    openai_key = get_openai_key()
    env = VerticalFarmHTNEnv(base_url="http://localhost:4649", agent_id="agent_1", puppet_id="farm_bot_1")
    user_interface = WebInterface
    htn_interface = PyHtnInterface
    agent = ValAgent(env, user_interface, htn_interface, openai_key)
    agent.start()

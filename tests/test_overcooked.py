from val.agent import ValAgent
from val.user_interfaces.console_interface import ConsoleUserInterface
from val.env_interfaces.overcooked_ai.overcooked_ai_env import OvercookedAIEnv
from val.htn_interfaces.basic_htn_interface import BasicHtnInterface
from val.htn_interfaces.py_htn_interface import PyHtnInterface
from val.utils import get_openai_key

if __name__ == "__main__":
    
    openai_key = get_openai_key()

    env = OvercookedAIEnv(player_id=1)
    # htn_interface = PyHtnInterface
    user_interface = ConsoleUserInterface
    htn_interface = BasicHtnInterface
    # htn_interface = PyHtnInterface


    agent = ValAgent(env, user_interface, htn_interface, openai_key)
    agent.start()


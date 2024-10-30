from val.agent import ValAgent
from val.user_interfaces.console_interface import ConsoleUserInterface
from val.user_interfaces.web_interface import WebInterface
from val.env_interfaces.space_transit.space_transit_env_htn import SpaceTransitEnvHTN 
from val.htn_interfaces.py_htn_interface_methods import PyHtnInterface
from val.utils import get_openai_key

if __name__ == "__main__":
    
    openai_key = get_openai_key()

    env = SpaceTransitEnvHTN()
    user_interface = ConsoleUserInterface
    # user_interface = WebInterface
    htn_interface = PyHtnInterface
    # htn_interface = PyHtnInterface


    agent = ValAgent(env, user_interface, htn_interface, openai_key)
    agent.start()


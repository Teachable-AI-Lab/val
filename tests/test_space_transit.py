from val.agent import ValAgent
from val.user_interfaces.console_interface import ConsoleUserInterface
from val.env_interfaces.space_transit.space_transit_env import SpaceTransitEnv 
from val.htn_interfaces.basic_htn_interface import BasicHtnInterface
from val.utils import get_openai_key

if __name__ == "__main__":
    
    openai_key = get_openai_key()

    env = SpaceTransitEnv()
    # htn_interface = PyHtnInterface
    user_interface = ConsoleUserInterface
    htn_interface = BasicHtnInterface


    agent = ValAgent(env, ConsoleUserInterface, BasicHtnInterface, openai_key)
    agent.start()

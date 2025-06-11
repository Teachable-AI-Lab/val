from val.agent import ValAgent
from val.htn_interfaces.py_htn_interface import PyHtnInterface
from val.user_interfaces.console_interface import ConsoleUserInterface
from val.user_interfaces.web_interface import WebInterface
from val.user_interfaces.speech_to_text_interface import SpeechToTextInterface
from val.env_interfaces.space_transit.space_transit_env import SpaceTransitEnv 
from val.htn_interfaces.basic_htn_interface import BasicHtnInterface
from val.utils import get_openai_key

if __name__ == "__main__":
    
    openai_key = get_openai_key()

    env = SpaceTransitEnv()
    # user_interface = ConsoleUserInterface
    # user_interface = WebInterface
    user_interface = SpeechToTextInterface
    # htn_interface = BasicHtnInterface
    htn_interface = PyHtnInterface


    agent = ValAgent(env, user_interface, htn_interface, openai_key)
    agent.start()


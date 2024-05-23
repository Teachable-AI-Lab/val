import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
import subprocess

from val.agent import ValAgent
from val.user_interfaces.console_interface import ConsoleUserInterface
from val.user_interfaces.web_interface import WebInterface
from val.env_interfaces.tictactoe.tictactoe_env import TicTacToeEnv 
from val.htn_interfaces.basic_htn_interface import BasicHtnInterface
from val.htn_interfaces.py_htn_interface import PyHtnInterface
from val.utils import get_openai_key

if __name__ == "__main__":
    
    openai_key = get_openai_key()

    env = TicTacToeEnv()
    # htn_interface = PyHtnInterface
    user_interface = WebInterface
    htn_interface = BasicHtnInterface
    # htn_interface = PyHtnInterface
    if user_interface == WebInterface:
        relative_path = os.path.join('..', 'val', 'val', 'user_interfaces', 'launch_server.py')
        target_file = os.path.abspath(relative_path)
        print(f"Target file path: {target_file}")
        process = subprocess.Popen(['python', target_file])      
    agent = ValAgent(env, user_interface, htn_interface, openai_key)
    agent.start()


from val.agent import ValAgent
from val.user_interfaces.console_interface import ConsoleUserInterface
from val.user_interfaces.web_interface import WebInterface
from val.user_interfaces.console_interface import ConsoleUserInterface
from val.env_interfaces.tictactoe.tictactoe_env import TicTacToeEnv 
from val.htn_interfaces.basic_htn_interface import BasicHtnInterface
from val.htn_interfaces.py_htn_interface import PyHtnInterface
from val.utils import get_env_config

if __name__ == "__main__":

    cfg = get_env_config()

    env = TicTacToeEnv()
    # user_interface = WebInterface
    user_interface = ConsoleUserInterface
    htn_interface = BasicHtnInterface
    # htn_interface = PyHtnInterface

    # if user_interface == WebInterface:
    #     relative_path = os.path.join('..', 'val', 'val', 'user_interfaces', 'launch_server.py')
    #     target_file = os.path.abspath(relative_path)
    #     print(f"Target file path: {target_file}")
    #     process = subprocess.Popen(['python', target_file])

    agent = ValAgent(env, user_interface, htn_interface,
                     openai_key=cfg["OPENAI_API_KEY"],
                     openai_url=cfg["OPENAI_BASE_URL"],
                     openai_model=cfg["OPENAI_MODEL"],
                     max_context_tokens=int(cfg["MAX_CONTEXT_TOKENS"] or 100_000))
    agent.start()


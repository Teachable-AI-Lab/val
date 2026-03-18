from val.agent import ValAgent
from val.user_interfaces.console_interface import ConsoleUserInterface
from val.env_interfaces.tictactoe.tictactoe_env import TicTacToeEnv 
from val.htn_interfaces.basic_htn_interface import BasicHtnInterface
from val.htn_interfaces.py_htn_interface import PyHtnInterface
from val.utils import get_env_config

if __name__ == "__main__":

    cfg = get_env_config()

    env = TicTacToeEnv()
    # htn_interface = PyHtnInterface
    user_interface = ConsoleUserInterface
    htn_interface = BasicHtnInterface
    #htn_interface = PyHtnInterface

    agent = ValAgent(env, user_interface, htn_interface,
                     openai_key=cfg["OPENAI_API_KEY"],
                     openai_url=cfg["OPENAI_BASE_URL"],
                     openai_model=cfg["OPENAI_MODEL"],
                     max_context_tokens=int(cfg["MAX_CONTEXT_TOKENS"] or 100_000))
    agent.start()


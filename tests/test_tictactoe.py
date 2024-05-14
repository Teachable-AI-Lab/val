from val.agent import ValAgent
from val.user_interfaces.console_interface import ConsoleUserInterface
from val.env_interfaces.tictactoe.tictactoe_env import TicTacToeEnv 
from val.htn_interfaces.basic_htn_interface import BasicHtnInterface
from val.utils import get_openai_key

if __name__ == "__main__":
    
    user_interface = ConsoleUserInterface()
    env_interface = TicTacToeEnv()
    # htn_interface = PyHtnInterface(env_interface)
    htn_interface = BasicHtnInterface(env_interface)

    openai_key = get_openai_key()

    agent = ValAgent(user_interface, env_interface, htn_interface, openai_key)

    while True:
        user_task = user_interface.request_user_task() 
        agent.interpret(user_task)


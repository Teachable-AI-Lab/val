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

async def run_render(env):
    while True:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                return
        env.render_state()
        pygame.display.flip()  # update the display
        await asyncio.sleep(0.03)  # Controls the frame rate


async def main():
    openai_key = get_openai_key()
    env = VerticalFarmHTNEnv(base_url="http://localhost:4649", agent_id="agent_1", puppet_id="farm_bot_1")
    user_interface = ConsoleUserInterface
    htn_interface = PyHtnInterface
    agent = ValAgent(env, user_interface, htn_interface, openai_key)

    # We use asyncio to concurrently run the blocking agent logic and the non-blocking render loop.
    await asyncio.gather(
        asyncio.to_thread(agent.start),  # Run the blocking agent logic in a background thread
        run_render(env)                  # Keep rendering frames on the main thread
    )



if __name__ == "__main__":
    asyncio.run(main())

import asyncio
import pygame
from val.env_interfaces.overcooked_ai.overcooked_ai_env import OvercookedAIEnv
from val.agent import ValAgent
from val.user_interfaces.console_interface import ConsoleUserInterface
from val.htn_interfaces.py_htn_interface import PyHtnInterface
from val.utils import get_openai_key


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
    env = OvercookedAIEnv(player_id=1, render=True)  # pygame init must be in main thread
    user_interface = ConsoleUserInterface
    htn_interface = PyHtnInterface
    agent = ValAgent(env, user_interface, htn_interface, openai_key)

    # We use asyncio to concurrently run the blocking agent logic and the non-blocking render loop.
    await asyncio.gather(
        asyncio.to_thread(agent.start),  # Run the blocking agent logic in a background thread
        run_render(env)                  # Keep rendering frames on the main thread
    )

# Below is an optional test action loop if you want to debug behavior directly.
# async def run_action_loop(env):
#     import random
#     while True:
#         env.execute_action(action_name="go_to", args=['onion'])  # 或 random.choice(["up", "down", "left", "right"])
#         await asyncio.sleep(0.5)

# async def main():
#     env = OvercookedAIEnv(player_id=1, render=True)
#     await asyncio.gather(
#         run_render(env),
#         run_action_loop(env)
#     )


if __name__ == "__main__":
    asyncio.run(main())





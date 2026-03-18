import asyncio
import pygame
from val.env_interfaces.overcooked_ai.overcooked_ai_env import OvercookedAIEnv
from val.agent import ValAgent
from val.user_interfaces.console_interface import ConsoleUserInterface
from val.user_interfaces.web_interface import WebInterface
from val.htn_interfaces.py_htn_interface import PyHtnInterface
from val.utils import get_env_config



async def run_render(env):
    while True:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                return
        env.render_state()
        pygame.display.flip()
        await asyncio.sleep(0.03)


async def main():
    cfg = get_env_config()
    env = OvercookedAIEnv(player_id=1, render=True)
    #user_interface = ConsoleUserInterface
    user_interface = WebInterface
    htn_interface = PyHtnInterface
    agent = ValAgent(env, user_interface, htn_interface,
                     openai_key=cfg["OPENAI_API_KEY"],
                     openai_url=cfg["OPENAI_BASE_URL"],
                     openai_model=cfg["OPENAI_MODEL"],
                     max_context_tokens=int(cfg["MAX_CONTEXT_TOKENS"] or 100_000))

    print("🤖 XAI-Enhanced VAL Agent with Overcooked")
    print("="*90)
    print("This version includes explainable AI features that will explain")
    print("why the agent makes certain decisions during task decomposition.")
    print("="*90)

    # Run the agent with XAI explanations
    await asyncio.gather(
        asyncio.to_thread(agent.start),
        run_render(env)
    )

if __name__ == "__main__":
    asyncio.run(main()) 

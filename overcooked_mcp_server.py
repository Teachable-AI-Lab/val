"""
MCP server for the Overcooked AI environment.

Exposes the full game state and all action primitives as MCP tools so that
any MCP-compatible agent can control the game without needing direct Python
access to OvercookedAIEnv.

Run with:
    python overcooked_mcp_server.py            # renders by default
    python overcooked_mcp_server.py --headless  # no pygame window
    python overcooked_mcp_server.py --terminal  # interactive terminal CLI
or register it in your MCP client config (e.g. Claude Desktop / claude_desktop_config.json).
"""

import argparse
import asyncio
import json
import sys
from typing import Any
from pprint import pprint

import mcp.server.stdio
import mcp.types as types
from mcp.server import Server
from openai import AsyncOpenAI

from val.env_interfaces.overcooked_ai.overcooked_ai_env import OvercookedAIEnv
from val.utils import get_env_config

# ---------------------------------------------------------------------------
# CLI flags — parsed once at startup
# ---------------------------------------------------------------------------

_parser = argparse.ArgumentParser(add_help=False)
_parser.add_argument("--headless", action="store_true", help="Disable pygame rendering.")
_parser.add_argument("--terminal", action="store_true", help="Run interactive terminal CLI.")
_args, _ = _parser.parse_known_args()

RENDER = not _args.headless

# ---------------------------------------------------------------------------
# Global environment instance (single-session, stateful)
# ---------------------------------------------------------------------------

_env: OvercookedAIEnv | None = None


def _get_env() -> OvercookedAIEnv:
    global _env
    if _env is None:
        raise RuntimeError("Environment not initialised. Call 'reset_env' first.")
    return _env


# ---------------------------------------------------------------------------
# MCP server
# ---------------------------------------------------------------------------

server = Server("overcooked")


@server.list_tools()
async def list_tools() -> list[types.Tool]:
    return [
        # ── Environment lifecycle ────────────────────────────────────────────
        types.Tool(
            name="reset_env",
            description=(
                "Initialise (or reset) the Overcooked environment. "
                "Must be called before any other tool. "
                "Returns a confirmation message and the starting game state. "
                "Rendering follows the --headless flag passed at server startup "
                "(render=True by default, False when --headless is set)."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "layout": {
                        "type": "string",
                        "description": (
                            "Name of the layout to use. "
                            "Default: 'asymmetric_advantages'. "
                            "See https://github.com/HumanCompatibleAI/overcooked_ai/tree/"
                            "cb2e50cae95accbe4618879d88e565c87c54b1c3/src/overcooked_ai_py/data/layouts"
                        ),
                        "default": "asymmetric_advantages",
                    },
                    "horizon": {
                        "type": "integer",
                        "description": "Maximum number of timesteps per episode.",
                        "default": 5000,
                    },
                    "player_id": {
                        "type": "integer",
                        "description": "Which player index the agent controls (0 or 1).",
                        "default": 0,
                    },
                },
                "required": [],
            },
        ),

        # ── Observation ──────────────────────────────────────────────────────
        types.Tool(
            name="get_state",
            description=(
                "Return the full game state as a JSON array. "
                "Each element is a dict describing one entity: players, "
                "ingredient dispensers (onion/tomato/dish), pots (with status "
                "and ingredient counts), serving pads, counter objects, "
                "terrain tiles, active orders, and the current timestep."
            ),
            inputSchema={"type": "object", "properties": {}, "required": []},
        ),
        # types.Tool(
        #     name="get_objects",
        #     description=(
        #         "Return the list of named objects currently present in the "
        #         "environment (players + any objects visible on counters or "
        #         "dispensers). Useful for knowing valid arguments to 'go_to'."
        #     ),
        #     inputSchema={"type": "object", "properties": {}, "required": []},
        # ),

        # ── Navigation ───────────────────────────────────────────────────────
        types.Tool(
            name="go_to",
            description=(
                "Navigate the player to stand adjacent to and face the named "
                "target object. The environment uses pathfinding internally. "
                "Valid targets: the ids from any objects in the state."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "target": {
                        "type": "string",
                        "description": "Name of the target object to navigate to.",
                    }
                },
                "required": ["target"],
            },
        ),

        # ── Cardinal movement ────────────────────────────────────────────────
        types.Tool(
            name="move",
            description="Move the player one grid cell in the given direction.",
            inputSchema={
                "type": "object",
                "properties": {
                    "direction": {
                        "type": "string",
                        "enum": ["up", "down", "left", "right"],
                        "description": "Direction to move.",
                    }
                },
                "required": ["direction"],
            },
        ),

        # ── Interaction ──────────────────────────────────────────────────────
        types.Tool(
            name="interact",
            description=(
                "Interact with whatever object the player is currently facing. "
                "Examples: pick up an onion from a dispenser, drop an ingredient "
                "into a pot, pick up a dish, plate cooked soup from a ready pot, "
                "or deliver plated soup at the serving pad."
            ),
            inputSchema={"type": "object", "properties": {}, "required": []},
        ),

        # ── Waiting ──────────────────────────────────────────────────────────
        types.Tool(
            name="wait",
            description=(
                "Idle for 20 timesteps. Use this to let a pot finish cooking "
                "before attempting to plate."
            ),
            inputSchema={"type": "object", "properties": {}, "required": []},
        ),
    ]


# ---------------------------------------------------------------------------
# Tool call handler
# ---------------------------------------------------------------------------

@server.call_tool()
async def call_tool(
    name: str, arguments: dict[str, Any]
) -> list[types.TextContent]:

    def ok(payload: Any) -> list[types.TextContent]:
        return [types.TextContent(type="text", text=json.dumps(payload, indent=2))]

    def err(msg: str) -> list[types.TextContent]:
        return [types.TextContent(type="text", text=json.dumps({"error": msg}))]

    # ── reset_env ────────────────────────────────────────────────────────────
    if name == "reset_env":
        global _env
        layout = arguments.get("layout", "asymmetric_advantages")
        horizon = int(arguments.get("horizon", 5000))
        player_id = int(arguments.get("player_id", 0))
        _env = OvercookedAIEnv(
            player_id=player_id, horizon=horizon, layout=layout, render=RENDER
        )
        state = _env.get_state()
        return ok({"message": "Environment initialised.", "state": state})

    # All other tools require an initialised env
    try:
        env = _get_env()
    except RuntimeError as exc:
        return err(str(exc))

    # ── get_state ────────────────────────────────────────────────────────────
    if name == "get_state":
        return ok(env.get_state())

    # ── get_objects ──────────────────────────────────────────────────────────
    elif name == "get_objects":
        return ok(env.get_objects())

    # ── go_to ────────────────────────────────────────────────────────────────
    elif name == "go_to":
        target = arguments.get("target", "")
        if not target:
            return err("'target' is required.")

        try:
            env.execute_action("go to", [target])
            pos, orr = env.get_player_pos_and_or()
            return ok({
                "message": f"Navigated to '{target}'.",
                "state": env.get_state(),
            })
        except:
            return err(f"'go to' failed, {target} is unreachable.")


    # ── move ─────────────────────────────────────────────────────────────────
    elif name == "move":
        direction = arguments.get("direction", "")
        if direction not in ("up", "down", "left", "right"):
            return err("'direction' must be one of: up, down, left, right.")
        env.execute_action(direction, [])
        return ok({
            "message": f"Moved {direction}.",
            "state": env.get_state(),
        })

    # ── interact ─────────────────────────────────────────────────────────────
    elif name == "interact":
        env.execute_action("interact", [])
        return ok({
            "message": "Interact executed.",
            "state": env.get_state(),
        })

    # ── wait ──────────────────────────────────────────────────────────────────
    elif name == "wait":
        env.execute_action("wait 20min", [])
        return ok({
            "message": "Waited 20 timesteps.",
            "state": env.get_state(),
        })

    else:
        return err(f"Unknown tool: '{name}'")


# ---------------------------------------------------------------------------
# Entry point — MCP stdio server
# ---------------------------------------------------------------------------

async def main():
    async with mcp.server.stdio.stdio_server() as (read_stream, write_stream):
        await server.run(
            read_stream,
            write_stream,
            server.create_initialization_options(),
        )


# ---------------------------------------------------------------------------
# Terminal CLI — interactive OpenAI tool-use loop
# ---------------------------------------------------------------------------

def _to_openai_tools(mcp_tools: list[types.Tool]) -> list[dict]:
    """Convert MCP Tool definitions to the OpenAI function-calling schema."""
    return [
        {
            "type": "function",
            "function": {
                "name": t.name,
                "description": t.description,
                "parameters": t.inputSchema,
            },
        }
        for t in mcp_tools
    ]


def _trim_messages(messages: list[dict], system: dict, keep_last: int = 20) -> list[dict]:
    """Drop the oldest non-system messages to stay within the context budget."""
    non_system = [m for m in messages if m is not system]
    trimmed = non_system[-keep_last:]
    # Some models (e.g. Qwen) require the conversation to start with a user
    # message.  If trimming removed all user messages, re-anchor to the most
    # recent user message still present in non_system.
    if not any(m.get("role") == "user" for m in trimmed):
        for m in reversed(non_system):
            if m.get("role") == "user":
                trimmed = [m] + trimmed
                break
    return [system] + trimmed


async def run_terminal_cli() -> None:
    cfg = get_env_config()

    api_key = cfg.get("OPENAI_API_KEY")
    base_url = cfg.get("OPENAI_BASE_URL")
    model = cfg.get("OPENAI_MODEL")
    max_context = int(cfg.get("MAX_CONTEXT_TOKENS") or 120_000)
    trim_threshold = max_context - 4_096  # reserve headroom for the next reply

    if not api_key:
        print("Error: OPENAI_API_KEY is not set in .env")
        return
    if not model:
        print("Error: OPENAI_MODEL is not set in .env")
        return

    client = AsyncOpenAI(api_key=api_key, base_url=base_url or None)

    # Load tools dynamically straight from this server's list_tools handler
    # so any future additions are picked up automatically.
    mcp_tools = await list_tools()
    openai_tools = _to_openai_tools(mcp_tools)

    system: dict = {
        "role": "system",
        "content": (
            "You are an AI agent playing Overcooked. "
            "Use the available tools to control the game. "
            "The environment has already been initialised — do not call reset_env unless the user explicitly asks to restart. "
            "You may chain multiple tool calls to complete a task before responding. "
            "If you are unsure what to do, cannot find a target, or have tried the same action repeatedly without success, "
            "stop calling tools and send a plain text message asking the user for guidance."
        ),
    }
    messages: list[dict] = [system]

    print(f"Overcooked terminal CLI  |  model={model}  |  max_context={max_context}")
    print("Type a command (or 'quit' to exit).\n")

    # Initialise the environment immediately so the game window appears on startup.
    await call_tool("reset_env", {})

    while True:
        try:
            user_input = await asyncio.to_thread(input, "> ")
        except (EOFError, KeyboardInterrupt):
            print("\nExiting.")
            break

        user_input = user_input.strip()
        if not user_input:
            continue
        if user_input.lower() in ("quit", "exit", "q"):
            break

        messages.append({"role": "user", "content": user_input})

        # Agentic loop — keep going until the model stops calling tools.
        while True:

            response = await client.chat.completions.create(
                model=model,
                messages=messages,
                tools=openai_tools,
                tool_choice="auto",
            )

            # Trim history if we're approaching the context limit.
            if response.usage and response.usage.total_tokens >= trim_threshold:
                messages = _trim_messages(messages, system)

            choice = response.choices[0]
            assistant_msg = choice.message

            # Append the raw assistant message (preserves tool_calls field).
            messages.append(assistant_msg.model_dump(exclude_unset=True))

            if choice.finish_reason == "tool_calls" and assistant_msg.tool_calls:
                for tc in assistant_msg.tool_calls:
                    try:
                        args = json.loads(tc.function.arguments or "{}")
                    except json.JSONDecodeError:
                        args = {}

                    print(f"  → {tc.function.name}({json.dumps(args)})")
                    results = await call_tool(tc.function.name, args)
                    result_text = results[0].text if results else "{}"
                    # Print a short preview so the user can follow along.
                    preview = result_text if len(result_text) <= 300 else result_text[:297] + "..."
                    print(f"  ← {preview}\n")

                    messages.append({
                        "role": "tool",
                        "tool_call_id": tc.id,
                        "content": result_text,
                    })
            else:
                # No more tool calls — print the final reply and wait for input.
                if assistant_msg.content:
                    print(f"\n{assistant_msg.content}\n")
                break


async def _terminal_main() -> None:
    """Entry point for --terminal: render loop + CLI running concurrently."""
    import pygame

    if RENDER:
        async def _render_loop():
            while True:
                if pygame.get_init():
                    for event in pygame.event.get():
                        if event.type == pygame.QUIT:
                            return
                await asyncio.sleep(0.033)

        await asyncio.gather(
            run_terminal_cli(),
            _render_loop(),
        )
    else:
        await run_terminal_cli()


if __name__ == "__main__":
    if _args.terminal:
        asyncio.run(_terminal_main())
    else:
        asyncio.run(main())

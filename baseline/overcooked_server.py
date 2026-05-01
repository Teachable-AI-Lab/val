from flask import Flask, send_from_directory
from flask_socketio import SocketIO, emit
import json
import re
import os
import asyncio
import pygame
from datetime import datetime, timezone
from typing import List, Tuple, Optional

from val.env_interfaces.overcooked_ai.overcooked_ai_env import OvercookedAIEnv
from val.gpt_completer import GPTCompleter
from val.utils import get_openai_config

app = Flask(__name__)
app.config['SECRET_KEY'] = 'your_secret_key'
socketio = SocketIO(app, cors_allowed_origins="*")

# Global variables
env = None
gpt_completer = None
conversation_history = []  # Store recent conversation history
MAX_HISTORY_LENGTH = 5  # Maximum number of conversation turns to keep
LOG_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'log.html'))


def append_user_log(event):
    """Append user action logs as JSON lines."""
    payload = event if isinstance(event, dict) else {"message": str(event)}
    payload.setdefault("server_timestamp", datetime.now(timezone.utc).isoformat())
    payload.setdefault("source", "overcooked_baseline")

    try:
        with open(LOG_PATH, 'a', encoding='utf-8') as log_file:
            log_file.write(json.dumps(payload, ensure_ascii=False) + '\n')
        return {"ok": True}
    except Exception as e:
        print(f"Error writing user log: {e}")
        return {"error": str(e)}

# Load OpenAI-compatible config
def load_openai_config():
    try:
        return get_openai_config()
    except Exception as e:
        print(f"Error loading OpenAI config: {e}")
        return {"api_key": "", "base_url": None, "model": None}

# Pygame rendering loop (async version)
async def run_render(env):
    """Run pygame rendering loop asynchronously
    
    This continuously handles pygame events and renders the game state.
    Similar to test_overcooked.py implementation.
    """
    if not env or not env.render:
        return
    
    print("Starting pygame render loop...")
    
    while True:
        try:
            # Handle pygame events (window close, etc.)
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    print("Pygame window closed")
                    pygame.quit()
                    return
            
            # Render the current state
            if env and env.render:
                env.render_state()
                pygame.display.flip()  # Update the display
            
            # Control frame rate (about 30 FPS)
            await asyncio.sleep(0.03)
        except Exception as e:
            print(f"Error in render loop: {e}")
            await asyncio.sleep(0.1)

# Initialize environment and GPT
def init_environment(enable_render=True):
    global env, gpt_completer
    try:
        config = load_openai_config()
        print(f"Using API profile: {config.get('profile', 'default')}")
        api_key = config.get("api_key")
        if not api_key:
            print("Warning: No API key found. GPT features will not work.")
        
        gpt_completer = GPTCompleter(config) if api_key else None
        
        # Initialize environment with rendering enabled
        # pygame init must be in main thread
        env = OvercookedAIEnv(player_id=0, horizon=5000, layout="counter_circuit_o_1order", render=enable_render)
        print("Environment initialized successfully")
        
        return True
    except Exception as e:
        print(f"Error initializing environment: {e}")
        return False

# Get available actions and objects
def get_available_actions_and_objects():
    """Get available actions and objects in the environment"""
    domain, descriptions = env.get_primary_actions()
    actions = list(domain.keys())
    objects = env.get_objects()
    return actions, objects, descriptions

# Build GPT prompt
def build_action_prompt(user_command: str, available_actions: List[str], 
                       available_objects: List[str], descriptions: dict,
                       current_state: dict) -> str:
    """Build prompt for converting user commands to actions"""
    global conversation_history
    
    # Format action descriptions
    actions_desc = []
    for action in available_actions:
        desc = descriptions.get(action, "No description available")
        actions_desc.append(f"- {action}: {desc}")
    
    actions_text = "\n".join(actions_desc)
    
    # Format objects (show only first 20 to avoid prompt being too long)
    objects_text = ", ".join(available_objects[:20])
    if len(available_objects) > 20:
        objects_text += f" and {len(available_objects) - 20} more objects"
    
    # Get current player state
    player_state = None
    for item in current_state:
        if item.get('is_me') == 'True':
            player_state = item
            break
    
    player_info = ""
    if player_state:
        holding = player_state.get('holding')
        holding_str = str(holding) if holding else "None"
        player_info = f"\nCurrent Player State:\n- Position: ({player_state.get('x')}, {player_state.get('y')})\n- Orientation: {player_state.get('orientation')}\n- Holding: {holding_str}"
    
    # Format conversation history
    history_text = ""
    if conversation_history:
        history_text = "\n\nRecent Conversation History:\n"
        for i, turn in enumerate(conversation_history[-MAX_HISTORY_LENGTH:], 1):
            user_msg = turn.get('user', '')
            assistant_msg = turn.get('assistant', '')
            if user_msg:
                history_text += f"{i}. User: {user_msg}\n"
            if assistant_msg:
                # Truncate assistant message if too long
                if len(assistant_msg) > 200:
                    assistant_msg = assistant_msg[:200] + "..."
                history_text += f"   Assistant: {assistant_msg}\n"
        history_text += "\n"
    
    prompt = f"""You are an intelligent game AI assistant. Your job is to understand user commands and convert them into a sequence of basic game actions, OR provide helpful conversational responses.

Available Basic Actions (you can only use these):
{actions_text}

Objects in the environment:
{objects_text}
{player_info}{history_text}
Current User Input: "{user_command}"

IMPORTANT INSTRUCTIONS:
1. If the user gives a command to DO something (like "cook onion", "get onion", "make soup"), you MUST break it down into a sequence of basic actions.
2. Complex tasks need multiple steps. Use pot1 or pot2 when going to a pot (e.g. go to pot1, go to pot2). For example:
   - "cook onion" means: get onion → go to pot1 → act  → get dish → go to pot2 (the opposite from previous step) → plate → deliver
   - "get onion" means: go to onion → act
   - "make soup" means: get onion → go to pot1 → act → get dish → go to pot2 (the opposite from previous step) → act 
3. Always think step by step and break down complex commands into the basic actions above.
4. If the user asks a QUESTION or makes a STATEMENT (not a command to do something), provide a helpful text response.

Response Format:
- For ACTION commands: Return a JSON object with "explanation" and "actions". Briefly explain in one or two sentences WHY you are doing these steps (e.g. which subgoal each part serves), then list the action array. Use "pot1" or "pot2" (not "pot") when the target is a pot.
  Example: {{"explanation": "I'll get an onion first, then bring it to the pot to cook.", "actions": [{{"action": "go to", "args": ["onion"]}}, ...]}}
- For QUESTIONS/STATEMENTS: Return: {{"type": "text", "message": "Your helpful response"}}

Examples of ACTION commands (return object with explanation + actions):
User: "go get onion"
Return: {{"explanation": "Going to the onion and acting to pick it up.", "actions": [{{"action": "go to", "args": ["onion"]}}, {{"action": "act", "args": []}}]}}

User: "cook onion"
Return: {{"explanation": "I'll fetch an onion, add it to the pot, wait for cooking, then get a dish and plate the soup.", "actions": [{{"action": "go to", "args": ["onion"]}}, {{"action": "act", "args": []}}, {{"action": "go to", "args": ["pot1"]}}, {{"action": "act", "args": []}}, {{"action": "wait 20min", "args": []}}, {{"action": "go to", "args": ["dish"]}}, {{"action": "act", "args": []}}, {{"action": "go to", "args": ["pot2"]}}, {{"action": "act", "args": []}}]}}


Examples of QUESTIONS/STATEMENTS (return text response):
User: "What can I do?"
Return: {{"type": "text", "message": "You can move around, act with objects like onions, pots, and serving stations. Try commands like 'go to onion' or 'cook onion'."}}

User: "I want to make soup"
Return: {{"type": "text", "message": "I'll help you make soup! The steps are: 1) Get an onion, 2) Go to the pot and add it, 3) Get a dish, 4) Plate the soup. Say 'cook onion' and I'll do it for you!"}}


CRITICAL: 
- If the user says something like "cook", "make", "get", "deliver" - these are ACTION commands. Break them down into basic actions.
- Always return valid JSON. Never return plain text for action commands.
- For ACTION commands, always include a brief "explanation" (why you are doing these steps) before listing "actions".
- Think about what steps are needed to complete the task, then return all steps as an action array.

Now respond to: "{user_command}"
"""
    return prompt

# Parse GPT response - returns either actions or text response
def parse_gpt_response(response: str) -> Tuple[Optional[List[Tuple[str, List[str]]]], Optional[str], Optional[str]]:
    """Parse GPT response and extract either actions or text response
    
    Returns:
        (actions, text_response, explanation): If actions, returns (actions_list, None, explanation_or_None). 
        If text response, returns (None, text_message, None).
    """
    actions = []
    text_response = None
    explanation = None
    
    try:
        # Try to parse JSON directly
        # Remove possible markdown code block markers
        response = response.strip()
        if response.startswith("```"):
            # Remove code block markers
            lines = response.split('\n')
            response = '\n'.join(lines[1:-1]) if len(lines) > 2 else response
        response = response.strip()
        
        # Try to parse JSON array or single JSON object
        parsed = json.loads(response)
        
        # Check if it's a text response
        if isinstance(parsed, dict) and parsed.get('type') == 'text':
            text_response = parsed.get('message', '')
            return (None, text_response, None)
        
        # Check if it's the new format: object with "explanation" and "actions"
        if isinstance(parsed, dict) and 'actions' in parsed:
            explanation = parsed.get('explanation') or None
            if isinstance(explanation, str):
                explanation = explanation.strip() or None
            arr = parsed['actions']
            if isinstance(arr, list):
                for item in arr:
                    if isinstance(item, dict) and 'action' in item:
                        action_name = item['action']
                        args = item.get('args', [])
                        if not isinstance(args, list):
                            args = [args] if args else []
                        actions.append((action_name, args))
                if actions:
                    return (actions, None, explanation)
        
        # Check if it's an action array (legacy format)
        if isinstance(parsed, list):
            for item in parsed:
                if isinstance(item, dict) and 'action' in item:
                    action_name = item['action']
                    args = item.get('args', [])
                    if not isinstance(args, list):
                        args = [args] if args else []
                    actions.append((action_name, args))
            if actions:
                return (actions, None, None)
        
        # Check if it's a single action object
        elif isinstance(parsed, dict) and 'action' in parsed:
            action_name = parsed['action']
            args = parsed.get('args', [])
            if not isinstance(args, list):
                args = [args] if args else []
            actions.append((action_name, args))
            return (actions, None, None)
            
    except json.JSONDecodeError:
        # If JSON parsing fails, try regex extraction for actions
        # Find patterns like "action": "xxx"
        action_pattern = r'"action"\s*:\s*"([^"]+)"'
        args_pattern = r'"args"\s*:\s*\[(.*?)\]'
        
        action_matches = re.findall(action_pattern, response)
        args_matches = re.findall(args_pattern, response)
        
        if action_matches:
            for i, action_name in enumerate(action_matches):
                args = []
                if i < len(args_matches):
                    args_str = args_matches[i]
                    # Extract parameters within quotes
                    arg_matches = re.findall(r'"([^"]+)"', args_str)
                    args = arg_matches
                
                actions.append((action_name, args))
            if actions:
                return (actions, None, None)
    
    # If no actions found and no text response, return None for both
    return (None, None, None)

# Process user command
def process_user_command(user_command: str) -> dict:
    """Process user command and return result"""
    global env, gpt_completer, conversation_history
    
    if not env:
        return {
            'success': False,
            'message': 'Environment not initialized',
            'actions': []
        }
    
    try:
        # Get current state and available actions
        current_state = env.get_state()
        available_actions, available_objects, descriptions = get_available_actions_and_objects()
        
        # Build prompt and call GPT
        if gpt_completer:
            prompt = build_action_prompt(user_command, available_actions, 
                                        available_objects, descriptions, current_state)
            
            # Call GPT
            gpt_response = gpt_completer.get_chat_gpt_completion(
                prompt, 
                temp=0.5,  # Slightly higher temperature for more creative problem-solving
                max_length=1024  # Increased to handle longer action sequences
            )
            
            # Parse GPT response
            actions, text_response, explanation = parse_gpt_response(gpt_response)
            
            # Handle text response (questions/explanations)
            if text_response:
                message = text_response
                
                # Update conversation history
                conversation_history.append({
                    'user': user_command,
                    'assistant': message
                })
                
                # Keep only recent history (limit to MAX_HISTORY_LENGTH)
                if len(conversation_history) > MAX_HISTORY_LENGTH:
                    conversation_history = conversation_history[-MAX_HISTORY_LENGTH:]
                
                return {
                    'success': True,
                    'message': message,
                    'actions': [],
                    'is_text_response': True,
                    'gpt_response': gpt_response
                }
            
            # Handle action execution
            if not actions:
                return {
                    'success': False,
                    'message': f'Unable to parse GPT response. GPT response: {gpt_response}',
                    'actions': [],
                    'gpt_response': gpt_response
                }
            
            # Execute actions
            executed_actions = []
            for action_name, args in actions:
                try:
                    success = env.execute_action(action_name, args)
                    if success:
                        executed_actions.append({
                            'name': action_name,
                            'args': args,
                            'success': True
                        })
                    else:
                        executed_actions.append({
                            'name': action_name,
                            'args': args,
                            'success': False,
                            'error': 'Execution failed'
                        })
                except Exception as e:
                    executed_actions.append({
                        'name': action_name,
                        'args': args,
                        'success': False,
                        'error': str(e)
                    })
            
            # Build response message (include brief explanation if present)
            action_summary = []
            for act in executed_actions:
                if act['success']:
                    action_summary.append(f"✓ {act['name']}({', '.join(act['args']) if act['args'] else 'no args'})")
                else:
                    action_summary.append(f"✗ {act['name']}({', '.join(act['args']) if act['args'] else 'no args'}) - {act.get('error', 'Unknown error')}")
            
            message = f"Processed your command: {user_command}\n\n"
            if explanation:
                message += f"Why: {explanation}\n\n"
            message += "Executed Actions:\n" + "\n".join(action_summary)
            
            # Update conversation history
            conversation_history.append({
                'user': user_command,
                'assistant': message
            })
            
            # Keep only recent history (limit to MAX_HISTORY_LENGTH)
            if len(conversation_history) > MAX_HISTORY_LENGTH:
                conversation_history = conversation_history[-MAX_HISTORY_LENGTH:]
            
            return {
                'success': True,
                'message': message,
                'actions': executed_actions,
                'is_text_response': False,
                'gpt_response': gpt_response
            }
        else:
            return {
                'success': False,
                'message': 'GPT service not initialized, unable to process command',
                'actions': []
            }
            
    except Exception as e:
        return {
            'success': False,
            'message': f'Error processing command: {str(e)}',
            'actions': []
        }

# SocketIO event handlers
@socketio.on('connect')
def handle_connect():
    global conversation_history
    print("Client connected")
    # Clear conversation history when a new client connects
    conversation_history = []
    emit('message', {
        'type': 'status',
        'message': 'Connected to server'
    })

@socketio.on('disconnect')
def handle_disconnect():
    print("Client disconnected")

@socketio.on('message')
def handle_message(data):
    """Handle general messages"""
    emit('message', data, broadcast=True)


@socketio.on('on_log')
@socketio.on('on log')
def handle_user_log(data):
    return append_user_log(data)


@socketio.on('user_command')
def handle_user_command(data):
    """Handle user command"""
    user_command = data.get('command', '').strip()
    
    if not user_command:
        emit('message', {
            'type': 'error',
            'message': 'Command cannot be empty'
        })
        return

    append_user_log({
        "event_type": "user_query",
        "function_name": "handle_user_command",
        "user_query": user_command,
        "client_timestamp": data.get("timestamp"),
    })
    
    # Send processing status
    emit('message', {
        'type': 'status',
        'message': f'Processing command: {user_command}...'
    })
    
    # Process command
    result = process_user_command(user_command)
    
    # Send result
    if result['success']:
        # Send main response
        emit('message', {
            'type': 'action_response',
            'message': result['message'],
            'action': result['actions'][0] if result['actions'] else None
        })
        
        # If there are multiple actions, send detailed information
        if len(result['actions']) > 1:
            for action in result['actions'][1:]:
                emit('message', {
                    'type': 'action_response',
                    'message': f"Executed: {action['name']}({', '.join(action['args']) if action['args'] else 'no args'})",
                    'action': action
                })
    else:
        emit('message', {
            'type': 'error',
            'message': result['message']
        })

# Serve frontend HTML file
@app.route('/')
def index():
    # Get current file directory
    current_dir = os.path.dirname(os.path.abspath(__file__))
    return send_from_directory(current_dir, 'overcooked_frontend.html')

# Run Flask server in a thread
def run_flask_server():
    """Run Flask server in a separate thread"""
    socketio.run(app, debug=False, host="localhost", port=4002, use_reloader=False, allow_unsafe_werkzeug=True)

# Main async function
async def main():
    """Main async function to run both Flask server and pygame rendering"""
    import sys
    
    # Check if render should be enabled (default: True)
    enable_render = True
    if len(sys.argv) > 1 and sys.argv[1] == '--no-render':
        enable_render = False
        print("Rendering disabled (--no-render flag)")
    
    print("Initializing environment...")
    if not init_environment(enable_render=enable_render):
        print("Environment initialization failed, server cannot start")
        return
    
    print("Starting server...")
    
    # Start Flask server in a background thread
    # We use asyncio to concurrently run the blocking Flask server and the non-blocking render loop
    tasks = []
    
    if enable_render and env and env.render:
        # Run render loop and Flask server concurrently
        tasks = [
            asyncio.to_thread(run_flask_server),  # Run Flask server in a background thread
            run_render(env)                        # Keep rendering frames on the main thread
        ]
    else:
        # Only run Flask server if rendering is disabled
        tasks = [asyncio.to_thread(run_flask_server)]
    
    try:
        await asyncio.gather(*tasks)
    except KeyboardInterrupt:
        print("\nShutting down...")
        if env and env.render:
            pygame.quit()

if __name__ == '__main__':
    asyncio.run(main())

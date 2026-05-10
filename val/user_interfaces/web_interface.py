import socketio
import json
import os
from html import escape
from datetime import datetime, timezone
from socketio.exceptions import TimeoutError
from typing import List
from typing import Optional
from pyhtn.htn import Task, Method, Operator, TaskEx, MethodEx, OperatorEx, tree_dict_to_str
from typing import List, Sequence, Optional, Tuple
from val.utils import normalize_grounding_args

LOG_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', 'log.html'))


def _clean_text(value):
    return ' '.join(str(value).replace('_', ' ').split())


def _task_phrase(name, args=None):
    cleaned_name = _clean_text(name)
    cleaned_args = [_clean_text(arg) for arg in (args or []) if str(arg).strip()]
    if cleaned_name.lower() == 'finish' and cleaned_args == ['onion']:
        return 'Finish onion order'

    parts = [cleaned_name]
    parts.extend(cleaned_args)
    return ' '.join(part for part in parts if part)


def _simplify_task_dict(task_dict):
    if not isinstance(task_dict, dict):
        return _clean_text(task_dict)

    name = task_dict.get('name') or task_dict.get('task_name') or ''
    args = task_dict.get('match')
    if args is None:
        args = task_dict.get('args', [])
    if not args and task_dict.get('V'):
        args = [task_dict.get('V')]
    return _task_phrase(name, args)


def _simplify_method_exec(method_exec):
    method_dict = method_exec.as_dict()
    return [
        _simplify_task_dict(child)
        for child in method_dict.get("child_data", [])
    ]


def _simplify_gui_subtasks(subtasks):
    return [
        _task_phrase(task.get('task_name'), task.get('args', []))
        for task in subtasks
        if isinstance(task, dict)
    ]

class WebInterface:
            
    def __init__(self, url="http://localhost:4002"):
        self.sio = socketio.Client()
        self.sio.connect(url)
        self.user_response = None
        self.response_received = False
        self.expected_type = None
        self.pending_interaction = None
        self.sio.on('message', self.on_message)

    def _append_log(self, payload):
        entry = {
            "event_type": "webinterface_user_response",
            "server_timestamp": datetime.now(timezone.utc).isoformat(),
            "source": "val_web_interface",
            **payload,
        }
        try:
            with open(LOG_PATH, 'a', encoding='utf-8') as log_file:
                log_file.write(json.dumps(entry, ensure_ascii=False) + '\n')
        except Exception as e:
            print("Failed to write web interface log:", e)

    def _set_pending_interaction(self, function_name, prompt):
        self.pending_interaction = {
            "function_name": function_name,
            "prompt": prompt,
        }

    def _summarize_response(self, response):
        if not isinstance(response, dict):
            return {"user_action": response}

        summary = {
            "user_action": response.get("user_choice", response),
        }
        if "index" in response:
            summary["index"] = response.get("index")

        edited = response.get("edited_decomposition")
        if isinstance(edited, dict):
            summary["edited_method"] = {
                "head": _simplify_task_dict(edited.get("head", {})),
                "subtasks": _simplify_gui_subtasks((edited.get("subtasks") or [[]])[0]),
            }
        return summary

    def _log_received_response(self, response):
        if self.pending_interaction is None:
            return

        pending = self.pending_interaction
        response_summary = self._summarize_response(response)
        prompt = pending.get("prompt", {})
        function_name = pending.get("function_name", "unknown")

        if function_name == "request_user_task":
            response_summary["user_query"] = _clean_text(response)
        elif function_name in {"ask_subtasks", "ask_rephrase"}:
            response_summary["user_text"] = _clean_text(response)

        if isinstance(response, dict):
            index = response.get("index", 0)
            methods = prompt.get("methods") or []
            if isinstance(index, int) and 0 <= index < len(methods):
                response_summary["selected_method"] = methods[index]

        self._append_log({
            "function_name": function_name,
            "prompt": prompt,
            "response": response_summary,
        })
        self.pending_interaction = None

    # This function is called when the client receives a message from the server 
    # change from previous version: event = self.sio.receive(), which is synchronous blocking call to wait for a server event 
    def on_message(self, data):
        print("Received message:", data)
        if isinstance(data, dict) and 'response' in data and data.get('type') == self.expected_type:
            self.user_response = data['response']
            self._log_received_response(self.user_response)
            self.response_received = True 
    
    
    def query_next_decomposition_with_edit(self, 
        task_exec: TaskEx, 
        method_execs: Sequence[MethodEx],
        available_actions: List[str],
        env_objects: List[str],
        decision_explanation: Optional[str] = None) -> Tuple[str, MethodEx, Sequence[Optional[float]]]:
        """
        Query user for decomposition choice with edit options
        
        Args:
            task_exec: The task execution to decompose
            method_execs: Available method executions for this task
            available_actions: List of available actions in the environment
            env_objects: List of available objects in the environment
            decision_explanation: Optional explanation for the default method choice
            
        Returns:
            Tuple of (user_choice, chosen_method_exec, rewards)
        """
        print("query_next_decomposition_with_edit called")
        print("task_exec:", task_exec)
        print("method_execs:", method_execs)
        print("method_execs type:", type(method_execs))
        print("method_execs length:", len(method_execs) if method_execs else "None or empty")
        
        self.user_response = None  
        self.response_received = False 
        self.expected_type = 'response_decomposition_with_edit' 
        
        # For NEW_ACTION or unknown tasks, go directly to add_method
        if(method_execs is None or len(method_execs) == 0):
            print("No method_execs available, going to add_method")
            return 'add_method', None, []

        # First, send thinking analysis to chatbot
        head = task_exec.as_dict()
        match = ' '.join(str(m).replace('_', ' ') for m in head['match'])
        task_name = head["name"]
        task_args = [str(m).replace('_', ' ') for m in head['match']]
        
        # Create thinking-style analysis text
        objects_text = ', '.join(env_objects[:5])
        if len(env_objects) > 5:
            objects_text += f" and {len(env_objects) - 5} more..."
        
        # Convert method_execs to subtasks format.
        subtasks = []
        for method_exec in method_execs:
            method_dict = method_exec.as_dict()
            child_list = method_dict.get("child_data", [])
            
            formatted_children = [
                {
                    "task_name": child["name"],
                    "args": [str(m).replace('_', ' ') for m in child["match"]],
                    "hash": child["id"]
                }
                for child in child_list
            ]
            subtasks.append(formatted_children)

        analysis_text = decision_explanation
        
        result = {
            "head": {
                "name": head["name"],
                "V": match,
                "hash": head["id"]
            },
            "user_task": f"{task_name} {' '.join(task_args)}",
            "task_name": task_name,
            "task_args": task_args,
            "analysis_text": analysis_text,
            "subtasks": subtasks,
            "available_actions": available_actions,
            "env_objects": env_objects
        }

        self._set_pending_interaction("query_next_decomposition_with_edit", {
            "head": _task_phrase(head["name"], task_args),
            "methods": [
                {"index": index, "subtasks": _simplify_method_exec(method_exec)}
                for index, method_exec in enumerate(method_execs)
            ],
        })
        
        self.sio.emit('message', {
            'type': 'confirm_best_match_decomposition',
            'text': result
        })
        print("Decomposition analysis and tree message emitted")
        
        # Wait for user response from chatbot buttons (Approve/Reject)
        self.user_response = None  
        self.response_received = False 
        self.expected_type = 'response_decomposition_with_edit'
        
        print("Waiting for user response from chatbot...")
        while not self.response_received:
            self.sio.sleep(0.1)
            
        response = self.user_response 
        rewards = [0.0] * len(method_execs)
        user_choice = response.get('user_choice', None)
        response_index = response.get('index', 0)
        if isinstance(response_index, str) and response_index.isdigit():
            response_index = int(response_index)
        if not isinstance(response_index, int) or response_index < 0 or response_index >= len(method_execs):
            response_index = 0
        
        print("response_index", response_index)
        print("user_choice", user_choice)
        
        # Handle different response types
        if user_choice == 'gui_edit':
            self.last_edited_decomposition = response.get('edited_decomposition', {})
            return user_choice, method_execs[response_index], rewards
        elif user_choice == 'approve':
            rewards[response_index] = 1.0
            return user_choice, method_execs[response_index], rewards 
        elif user_choice == 'reject':
            # For now, treat reject as add_method - user wants to create new method
            return 'add_method', None, []
        
        # Default to add_method
        return 'add_method', None, []
    
    def display_added_method(self, task_exec: TaskEx, 
        method_exec: MethodEx):
        self.user_response = None  
        self.response_received = False 
        self.expected_type = 'response_decomposition' 
        head = task_exec.as_dict()
        match = ' '.join(str(m).replace('_', ' ') for m in head['match'])

        # Step 2: build subtasks
        subtasks = []
        method_dict = method_exec.as_dict()
        child_list = method_dict.get("child_data", [])
        
        # Convert each child dict to the desired format
        formatted_children = [
            {
                "task_name": child["name"],
                "args": [str(m).replace('_', ' ') for m in child["match"]],
                "hash": child["id"]
            }
            for child in child_list
        ]
        subtasks.append(formatted_children)

        # Step 3: combine everything into one dict
        result = {
            "head": {
                "name": head["name"],
                "V": match,  # Or use a cleaner version if needed
                "hash": head["id"]
            },
            "subtasks": subtasks
        }

        self.user_response = None  
        self.response_received = False

        self.sio.emit('message', {'type': 'display_added_method', 'text': result})
        print("The message is emitted")
        while not self.response_received:
            self.sio.sleep(0.1)
            
        index = self.user_response 
        print("prepared to return")

        return

    def finish_task(self) -> None:
        self.user_response = None
        self.response_received = False
        self.expected_type = 'finish_task_response'
        self._set_pending_interaction("finish_task", {
            "question": "The task is complete. Click Finish Task to start a new task."
        })
        self.sio.emit('message', {
            'type': 'task_completed',
            'text': 'The task is complete.'
        })
        print("Task completion message emitted")
        while not self.response_received:
            self.sio.sleep(0.1)
        return
    
    def check_for_break(self) -> bool:
        return False
        
    
    def display_known_tasks(self, tasks: List[str]):
        text = "\n".join([f"({i}): {task}" for i, task in enumerate(tasks)])
        self.sio.emit('message', {'type': 'display_known_tasks',
                                  'text': "Those are the actions I know:" + text})
        return


    def display_method_creation(self, message: str, task_name: str = None, subtasks: List[str] = None, preconditions: List[str] = None):
        """
        Display when a new method is being created
        Args:
            message: Simple message to display
            task_name: The task name (optional)
            subtasks: List of subtasks (optional)
            preconditions: List of preconditions (optional)
        """
        if task_name and subtasks:
            # Full method creation display
            subtasks_text = ", ".join(subtasks)
            creation_text = f"⚙️ **Creating New Method:** `{task_name}`\n\n**Subtasks:** {subtasks_text}"
            
            if preconditions and len(preconditions) > 0:
                creation_text += f"\n\n**Preconditions:** {', '.join(preconditions)}"
        else:
            # Simple message display
            creation_text = f"⚙️ **Add New Method**\n\n{message}"
        
        self.sio.emit('message', {'type': 'display_method_creation', 'text': creation_text})
        print("Method creation message emitted")
        return

    def display_edit_options(self, message: str):
        """
        Display editing options for existing decompositions
        Args:
            message: Message to display
        """
        self.sio.emit('message', {'type': 'display_edit_options', 'text': f"✏️ **Edit Decomposition**\n\n{message}"})
        print("Edit options message emitted")
        return

    
    def request_user_task(self) -> str:
        self.user_response = None  
        self.response_received = False 
        self._set_pending_interaction("request_user_task", {
            "question": "How can I help you today?"
        })
        self.sio.emit('message', {'type': 'request_user_task', 'text': 'How can I help you today?'})
        print("The message is emitted")
        self.expected_type = 'confirm_response'
        while not self.response_received:
            self.sio.sleep(0.1)
        print('received')
        return self.user_response 
    
    def ask_subtasks(self, user_task: str, task_exec: Optional[TaskEx] = None) -> str:
        self.user_response = None  
        self.response_received = False 
        self.expected_type = 'confirm_response'
        task_hash = None
        if task_exec is not None:
            try:
                task_hash = task_exec.as_dict().get("id")
            except Exception:
                task_hash = None

        self._set_pending_interaction("ask_subtasks", {
            "user_task": _clean_text(user_task),
            "question": f"What are the steps for completing the task '{user_task}'?",
        })
        self.sio.emit('message', {
            'type': 'ask_subtasks',
            'text': f"What are the steps for completing the task '{user_task}'?",
            'task_hash': task_hash
        })
        while not self.response_received:
            self.sio.sleep(0.1)
        print('received response:', self.user_response)
        return self.user_response
    
    def ask_rephrase(self, user_tasks: str) -> str:
        self.user_response = None  
        self.response_received = False
        self.expected_type = 'confirm_response' 
        self._set_pending_interaction("ask_rephrase", {
            "user_tasks": _clean_text(user_tasks),
            "question": f"Sorry about that. Can you rephrase the tasks '{user_tasks}'?",
        })
        self.sio.emit('message', {
            'type': 'ask_rephrase', 
            'text': f"Sorry about that. Can you rephrase the tasks '{user_tasks}'?"
        })
        while not self.response_received:
            self.sio.sleep(0.1)
        print('received response:', self.user_response)
        return self.user_response

    def segment_confirmation(self, steps: List[str]) -> bool:
        # set to None to reset the stored user response
        self.user_response = None
        self.response_received = False
        self.expected_type = 'confirm_response' 
        question_text = (
            "This is the step of your command, right?"
            if len(steps) == 1
            else "These are the individual steps of your command, right?"
        )
        formatted_steps = '<br>'.join(
            f"{index}. {escape(str(step))}"
            for index, step in enumerate(steps, start=1)
        )
        message_text = f"{question_text}<br><br>{formatted_steps}"
        self._set_pending_interaction("segment_confirmation", {
            "question": question_text,
            "steps": [_clean_text(step) for step in steps],
        })
        self.sio.emit('message', {'type': 'segment_confirmation', 
                                  'text': message_text,
                                  'steps': steps})
        while not self.response_received:
            self.sio.sleep(0.1)
        print('received response:', self.user_response)
        return 'yes' == self.user_response

    def correct_grounding(self, user_task: str, task_name: str, task_args: List[str], env_objects: List[str], available_actions: List[str]) -> tuple[str, List[str]]:
        """
        Allow user to correct the grounding result (action and objects)
        Returns (corrected_task_name, corrected_task_args)
        """
        self.user_response = None  
        self.response_received = False 
        self.expected_type = 'correct_grounding_response'
        env_objects=list(set(env_objects))
        available_actions=list(set(available_actions))
        self._set_pending_interaction("correct_grounding", {
            "user_task": _clean_text(user_task),
            "current_grounding": _task_phrase(task_name, task_args),
        })
        self.sio.emit('message', {
            'type': 'correct_grounding',
            'text': f"Correct the grounding for: '{user_task}'",
            'current_action': task_name,
            'current_objects': task_args,
            'available_objects': env_objects,
            'available_actions': available_actions
        })
        
        while not self.response_received:
            self.sio.sleep(0.1)
        
        # Parse response - expected format: "action:object1,object2"
        response = self.user_response
        if ':' in response:
            corrected_task_name, objects_str = response.split(':', 1)
            corrected_task_args = [obj.strip() for obj in objects_str.split(',') if obj.strip()]
        else:
            corrected_task_name = task_name
            corrected_task_args = task_args
        corrected_task_args = normalize_grounding_args(corrected_task_name, corrected_task_args)
        
        # After grounding correction, just return
        # Both thinking analysis and decomposition tree will be shown together in the main loop
        return corrected_task_name, corrected_task_args

    
    
if __name__ == "__main__":
    web_interface = WebInterface()
    print(web_interface.query_next_decomposition_and_rewards(
        TaskEx("task1", "arg1"),
        [MethodEx("method1", "arg1"), MethodEx("method2", "arg2")]
    ))


import sqlite3
import json
import uuid
import time
from typing import List, Dict, Any, Optional
from dataclasses import dataclass
from enum import Enum


class EventType(Enum):
    # User interaction events
    USER_TASK_REQUEST = "user_task_request"
    USER_SEGMENT_CONFIRMATION = "user_segment_confirmation"
    USER_MAP_CONFIRMATION = "user_map_confirmation"
    USER_MAP_CORRECTION = "user_map_correction"
    USER_GROUND_CONFIRMATION = "user_ground_confirmation"
    USER_GROUND_CORRECTION = "user_ground_correction"
    USER_GEN_CONFIRMATION = "user_gen_confirmation"
    USER_GEN_CORRECTION = "user_gen_correction"
    USER_DECOMPOSITION_SELECTION = "user_decomposition_selection"
    USER_SUBTASK_DESCRIPTION = "user_subtask_description"
    USER_REPHRASE_REQUEST = "user_rephrase_request"
    
    # LLM processing events
    LLM_SEGMENTATION = "llm_segmentation"
    LLM_MAPPING = "llm_mapping"
    LLM_GROUNDING = "llm_grounding"
    LLM_GENERATION = "llm_generation"
    LLM_VERBALIZATION = "llm_verbalization"
    LLM_PARAPHRASE_CHECK = "llm_paraphrase_check"
    LLM_TASK_NAMING = "llm_task_naming"
    
    # HTN operations
    HTN_TASK_ADDITION = "htn_task_addition"
    HTN_METHOD_ADDITION = "htn_method_addition"
    HTN_PLANNING_STEP = "htn_planning_step"
    HTN_METHOD_EXECUTION = "htn_method_execution"
    HTN_TASK_EXECUTION = "htn_task_execution"
    
    # Environment events
    ENV_STATE_CHANGE = "env_state_change"
    ENV_ACTION_EXECUTION = "env_action_execution"
    
    # System events
    SESSION_START = "session_start"
    SESSION_END = "session_end"
    ERROR = "error"


@dataclass
class LogEvent:
    """Data class for representing a log event"""
    session_id: str
    event_type: EventType
    timestamp: float
    event_data: Dict[str, Any]
    env_state: Optional[Dict[str, Any]] = None
    htn_knowledge_base: Optional[Dict[str, Any]] = None


class ValLogger:
    """SQLite-based logging system for VAL agent events"""
    
    def __init__(self, db_path: str = "val/val_events.db"):
        self.db_path = db_path
        self.session_id = str(uuid.uuid4())
        self.init_database()
    
    def init_database(self):
        """Initialize the SQLite database with required tables"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS events (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    session_id TEXT NOT NULL,
                    event_type TEXT NOT NULL,
                    timestamp REAL NOT NULL,
                    event_data TEXT NOT NULL,
                    env_state TEXT,
                    htn_knowledge_base TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS sessions (
                    session_id TEXT PRIMARY KEY,
                    start_time REAL NOT NULL,
                    end_time REAL,
                    environment_type TEXT,
                    user_interface_type TEXT,
                    htn_interface_type TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            # Create indexes for better query performance
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_session_id ON events(session_id)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_event_type ON events(event_type)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_timestamp ON events(timestamp)')
            
            conn.commit()
    
    def log_event(self, event_type: EventType, event_data: Dict[str, Any], 
                  env_state: Optional[Dict[str, Any]] = None, 
                  htn_knowledge_base: Optional[Dict[str, Any]] = None):
        """Log an event to the database"""
        event = LogEvent(
            session_id=self.session_id,
            event_type=event_type,
            timestamp=time.time(),
            event_data=event_data,
            env_state=env_state,
            htn_knowledge_base=htn_knowledge_base
        )
        
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO events (session_id, event_type, timestamp, event_data, env_state, htn_knowledge_base)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (
                event.session_id,
                event.event_type.value,
                event.timestamp,
                json.dumps(event.event_data),
                json.dumps(event.env_state) if event.env_state else None,
                json.dumps(event.htn_knowledge_base) if event.htn_knowledge_base else None
            ))
            conn.commit()
    
    def start_session(self, environment_type: str, user_interface_type: str, htn_interface_type: str):
        """Log session start"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO sessions (session_id, start_time, environment_type, user_interface_type, htn_interface_type)
                VALUES (?, ?, ?, ?, ?)
            ''', (self.session_id, time.time(), environment_type, user_interface_type, htn_interface_type))
            conn.commit()
        
        self.log_event(EventType.SESSION_START, {
            "environment_type": environment_type,
            "user_interface_type": user_interface_type,
            "htn_interface_type": htn_interface_type
        })
    
    def end_session(self):
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute('''
                UPDATE sessions SET end_time = ? WHERE session_id = ?
            ''', (time.time(), self.session_id))
            conn.commit()
        
        self.log_event(EventType.SESSION_END, {})
    
    def log_user_task_request(self, user_task: str):
        self.log_event(EventType.USER_TASK_REQUEST, {
            "user_task": user_task
        })
    
    def log_llm_segmentation(self, user_tasks: str, segmented_tasks: List[str], llm_response: str):
        self.log_event(EventType.LLM_SEGMENTATION, {
            "user_tasks": user_tasks,
            "segmented_tasks": segmented_tasks,
            "llm_response": llm_response
        })
    
    def log_user_segment_confirmation(self, segmented_tasks: List[str], confirmed: bool):
        self.log_event(EventType.USER_SEGMENT_CONFIRMATION, {
            "segmented_tasks": segmented_tasks,
            "confirmed": confirmed
        })
    
    def log_llm_mapping(self, user_task: str, mapped_task: Optional[str], llm_response: str):
        self.log_event(EventType.LLM_MAPPING, {
            "user_task": user_task,
            "mapped_task": mapped_task,
            "llm_response": llm_response
        })
    
    def log_user_map_confirmation(self, user_task: str, task_name: str, confirmed: bool):
        self.log_event(EventType.USER_MAP_CONFIRMATION, {
            "user_task": user_task,
            "task_name": task_name,
            "confirmed": confirmed
        })
    
    def log_user_map_correction(self, user_task: str, available_tasks: List[str], selected_index: Optional[int]):
        self.log_event(EventType.USER_MAP_CORRECTION, {
            "user_task": user_task,
            "available_tasks": available_tasks,
            "selected_index": selected_index
        })
    
    def log_llm_grounding(self, user_task: str, task_name: str, grounded_args: List[str], llm_response: str):
        self.log_event(EventType.LLM_GROUNDING, {
            "user_task": user_task,
            "task_name": task_name,
            "grounded_args": grounded_args,
            "llm_response": llm_response
        })
    
    def log_user_ground_confirmation(self, task_name: str, task_args: List[str], confirmed: bool):
        self.log_event(EventType.USER_GROUND_CONFIRMATION, {
            "task_name": task_name,
            "task_args": task_args,
            "confirmed": confirmed
        })
    
    def log_user_ground_correction(self, task_name: str, original_args: List[str], corrected_args: List[str]):
        self.log_event(EventType.USER_GROUND_CORRECTION, {
            "task_name": task_name,
            "original_args": original_args,
            "corrected_args": corrected_args
        })
    
    def log_llm_generation(self, user_task: str, task_name: str, generated_args: List[str], llm_response: str):
        self.log_event(EventType.LLM_GENERATION, {
            "user_task": user_task,
            "task_name": task_name,
            "generated_args": generated_args,
            "llm_response": llm_response
        })
    
    def log_user_gen_confirmation(self, user_task: str, task_name: str, task_args: List[str], confirmed: bool):
        self.log_event(EventType.USER_GEN_CONFIRMATION, {
            "user_task": user_task,
            "task_name": task_name,
            "task_args": task_args,
            "confirmed": confirmed
        })
    
    def log_user_gen_correction(self, task_name: str, original_args: List[str], corrected_args: List[str]):
        self.log_event(EventType.USER_GEN_CORRECTION, {
            "task_name": task_name,
            "original_args": original_args,
            "corrected_args": corrected_args
        })
    
    def log_llm_verbalization(self, task_name: str, task_args: List[str], verbalized_task: str):
        self.log_event(EventType.LLM_VERBALIZATION, {
            "task_name": task_name,
            "task_args": task_args,
            "verbalized_task": verbalized_task
        })
    
    def log_llm_paraphrase_check(self, verbalized_task: str, user_task: str, is_paraphrase: bool):
        self.log_event(EventType.LLM_PARAPHRASE_CHECK, {
            "verbalized_task": verbalized_task,
            "user_task": user_task,
            "is_paraphrase": is_paraphrase
        })
    
    def log_llm_task_naming(self, user_task: str, task_name: str, llm_response: str):
        self.log_event(EventType.LLM_TASK_NAMING, {
            "user_task": user_task,
            "task_name": task_name,
            "llm_response": llm_response
        })
    
    def log_htn_task_addition(self, tasks: List[Dict[str, Any]]):
        self.log_event(EventType.HTN_TASK_ADDITION, {
            "tasks": tasks
        })
    
    def log_htn_method_addition(self, method_name: str, method_args: List[str], subtasks: List[str]):
        self.log_event(EventType.HTN_METHOD_ADDITION, {
            "method_name": method_name,
            "method_args": method_args,
            "subtasks": subtasks
        })
    
    def log_htn_planning_step(self, task_exec: str, method_execs: List[str], selected_method: Optional[str]):
        self.log_event(EventType.HTN_PLANNING_STEP, {
            "task_exec": task_exec,
            "method_execs": method_execs,
            "selected_method": selected_method
        })
    
    def log_user_decomposition_selection(self, task_exec: str, method_execs: List[str], selected_index: Optional[int], rewards: List[float]):
        self.log_event(EventType.USER_DECOMPOSITION_SELECTION, {
            "task_exec": task_exec,
            "method_execs": method_execs,
            "selected_index": selected_index,
            "rewards": rewards
        })
    
    def log_user_subtask_description(self, task_name: str, user_subtasks: str): 
        self.log_event(EventType.USER_SUBTASK_DESCRIPTION, {
            "task_name": task_name,
            "user_subtasks": user_subtasks
        })
    
    def log_user_rephrase_request(self, original_tasks: str, rephrased_tasks: str):
        self.log_event(EventType.USER_REPHRASE_REQUEST, {
            "original_tasks": original_tasks,
            "rephrased_tasks": rephrased_tasks
        })
    
    def log_env_state_change(self, old_state: Dict[str, Any], new_state: Dict[str, Any]):
        self.log_event(EventType.ENV_STATE_CHANGE, {
            "old_state": old_state,
            "new_state": new_state
        })
    
    def log_env_action_execution(self, action_name: str, action_args: List[str], success: bool):
        self.log_event(EventType.ENV_ACTION_EXECUTION, {
            "action_name": action_name,
            "action_args": action_args,
            "success": success
        })
    
    def log_error(self, error_type: str, error_message: str, stack_trace: Optional[str] = None):
        self.log_event(EventType.ERROR, {
            "error_type": error_type,
            "error_message": error_message,
            "stack_trace": stack_trace
        })
    
    def get_session_events(self, session_id: Optional[str] = None) -> List[Dict[str, Any]]:
        if session_id is None:
            session_id = self.session_id
        
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT * FROM events WHERE session_id = ? ORDER BY timestamp
            ''', (session_id,))
            
            events = []
            for row in cursor.fetchall():
                events.append({
                    "id": row[0],
                    "session_id": row[1],
                    "event_type": row[2],
                    "timestamp": row[3],
                    "event_data": json.loads(row[4]),
                    "env_state": json.loads(row[5]) if row[5] else None,
                    "htn_knowledge_base": json.loads(row[6]) if row[6] else None,
                    "created_at": row[7]
                })
            
            return events
    
    def get_session_summary(self, session_id: Optional[str] = None) -> Dict[str, Any]:
        if session_id is None:
            session_id = self.session_id
        
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT * FROM sessions WHERE session_id = ?
            ''', (session_id,))
            
            session_row = cursor.fetchone()
            if not session_row:
                return None
            
            cursor.execute('''
                SELECT event_type, COUNT(*) as count FROM events 
                WHERE session_id = ? GROUP BY event_type
            ''', (session_id,))
            
            event_counts = dict(cursor.fetchall())
            
            return {
                "session_id": session_row[0],
                "start_time": session_row[1],
                "end_time": session_row[2],
                "environment_type": session_row[3],
                "user_interface_type": session_row[4],
                "htn_interface_type": session_row[5],
                "created_at": session_row[6],
                "event_counts": event_counts
            } 
# VAL Agent Logging System

## Overview

The logging system tracks every event, including:

- **User Interactions**: Task requests, confirmations, corrections, and selections
- **LLM Operations**: Segmentation, mapping, grounding, generation, verbalization, and paraphrase checking
- **HTN Operations**: Task additions, method additions, planning steps, and executions
- **Environment Events**: State changes and action executions
- **System Events**: Session start/end and error handling

## Database Schema

### Events Table
```sql
CREATE TABLE events (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id TEXT NOT NULL,
    event_type TEXT NOT NULL,
    timestamp REAL NOT NULL,
    event_data TEXT NOT NULL,
    env_state TEXT,
    htn_knowledge_base TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

### Sessions Table
```sql
CREATE TABLE sessions (
    session_id TEXT PRIMARY KEY,
    start_time REAL NOT NULL,
    end_time REAL,
    environment_type TEXT,
    user_interface_type TEXT,
    htn_interface_type TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

## Event Types

### User Interaction Events
- `user_task_request`: User requests a task
- `user_segment_confirmation`: User confirms task segmentation
- `user_map_confirmation`: User confirms task mapping
- `user_map_correction`: User corrects task mapping
- `user_ground_confirmation`: User confirms argument grounding
- `user_ground_correction`: User corrects argument grounding
- `user_gen_confirmation`: User confirms argument generation
- `user_gen_correction`: User corrects argument generation
- `user_decomposition_selection`: User selects HTN decomposition
- `user_subtask_description`: User describes subtasks
- `user_rephrase_request`: User rephrases tasks

### LLM Processing Events
- `llm_segmentation`: LLM segments user tasks
- `llm_mapping`: LLM maps tasks to HTN methods
- `llm_grounding`: LLM grounds task arguments
- `llm_generation`: LLM generates task arguments
- `llm_verbalization`: LLM verbalizes tasks
- `llm_paraphrase_check`: LLM checks paraphrasing
- `llm_task_naming`: LLM names new tasks

### HTN Operations
- `htn_task_addition`: Tasks added to HTN
- `htn_method_addition`: Methods added to HTN
- `htn_planning_step`: HTN planning step
- `htn_method_execution`: HTN method execution
- `htn_task_execution`: HTN task execution

### Environment Events
- `env_state_change`: Environment state change
- `env_action_execution`: Environment action execution

### System Events
- `session_start`: Session begins
- `session_end`: Session ends
- `error`: System error

## Usage

### Running with Logging

The logging system is automatically integrated into the VAL agent. When you run the agent, it will:

1. Create a new session with a unique ID
2. Log all events with environment state and HTN knowledge base
3. Store everything in `val/val_events.db`

```bash
# Run the overcooked test with logging
python tests/test_overcooked.py
```

### Viewing Logs

Use the provided log viewer script:

```bash
# View session summary
python val/view_logs.py

# View specific session events
python val/view_logs.py --session <session_id>

# View event type statistics
python val/view_logs.py --types

# View recent events
python val/view_logs.py --recent 10
```

### Testing the Logging System

Run the standalone test:

```bash
python tests/test_logging.py
```

## Implementation Details

### Integration Points

The logging system is integrated into `val/agent.py` at the following key points:

1. **Agent Initialization**: Creates logger and starts session
2. **User Task Request**: Logs when user requests tasks
3. **LLM Operations**: Logs all GPT completions and responses
4. **User Confirmations**: Logs all user confirmations and corrections
5. **HTN Operations**: Logs task additions, method additions, and planning steps
6. **Error Handling**: Logs exceptions and session end


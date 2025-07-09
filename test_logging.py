#!/usr/bin/env python3
"""
Test script for the VAL logging system
"""

import sqlite3
import json
from val.logging_system import ValLogger, EventType

def test_logging_system():
    """Test the logging system with sample events"""
    
    logger = ValLogger("test_events.db")
    logger.start_session("TestEnv", "TestUI", "TestHTN")    
    logger.log_user_task_request("cook an onion")
    
    logger.log_llm_segmentation(
        "cook an onion", 
        ["cook an onion"], 
        "1. \"cook an onion\" (resolved pronouns: \"cook an onion\")"
    )
    
    logger.log_user_segment_confirmation(["cook an onion"], True)    
    logger.log_llm_mapping("cook an onion", "cook", "a) cook")    
    logger.log_user_map_confirmation("cook an onion", "cook", True)    
    logger.log_llm_grounding("cook an onion", "cook", ["onion"], "cook(onion)")    
    logger.log_user_ground_confirmation("cook", ["onion"], True)    
    logger.log_htn_task_addition([{"name": "cook", "arguments": ["onion"]}])    
    logger.log_htn_method_addition("cook", ["X"], ["get_ingredient", "heat_pan", "cook_ingredient"])
    logger.log_user_decomposition_selection("cook(onion)", ["method1", "method2"], 0, [1.0, -1.0])    
    logger.end_session()
    print("Test events logged successfully!")
    events = logger.get_session_events()
    print(f"\nRetrieved {len(events)} events:")
    
    for i, event in enumerate(events):
        print(f"\nEvent {i+1}:")
        print(f"  Type: {event['event_type']}")
        print(f"  Timestamp: {event['timestamp']}")
        print(f"  Data: {json.dumps(event['event_data'], indent=2)}")
        if event['env_state']:
            print(f"  Env State: {json.dumps(event['env_state'], indent=2)}")
        if event['htn_knowledge_base']:
            print(f"  HTN KB: {json.dumps(event['htn_knowledge_base'], indent=2)}")
    
    # Get session summary
    summary = logger.get_session_summary()
    print("\nSession Summary:")
    print(f"  Session ID: {summary['session_id']}")
    print(f"  Environment: {summary['environment_type']}")
    print(f"  User Interface: {summary['user_interface_type']}")
    print(f"  HTN Interface: {summary['htn_interface_type']}")
    print(f"  Event Counts: {summary['event_counts']}")

def inspect_database():
    """Inspect the SQLite database structure"""
    
    with sqlite3.connect("test_events.db") as conn:
        cursor = conn.cursor()
        
        # Show tables
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
        tables = cursor.fetchall()
        print("Tables in database:")
        for table in tables:
            print(f"  - {table[0]}")
        

        cursor.execute("PRAGMA table_info(events);")
        columns = cursor.fetchall()
        print("\nEvents table structure:")
        for col in columns:
            print(f"  - {col[1]} ({col[2]})")
        
        cursor.execute("PRAGMA table_info(sessions);")
        columns = cursor.fetchall()
        print("\nSessions table structure:")
        for col in columns:
            print(f"  - {col[1]} ({col[2]})")

if __name__ == "__main__":
    print("Testing VAL Logging System")
    print("=" * 50)
    
    test_logging_system()
    
    print("\n" + "=" * 50)
    print("Database Inspection")
    print("=" * 50)
    
    inspect_database() 
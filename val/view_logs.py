#!/usr/bin/env python3
"""
Script to view and analyze VAL agent logs
"""

import sqlite3
import json
import argparse
from datetime import datetime

def view_session_summary(db_path: str = "val/val_events.db"):
    """
    View summary of all sessions
    """
    with sqlite3.connect(db_path) as conn:
        cursor = conn.cursor()
        cursor.execute('''
            SELECT session_id, start_time, end_time, environment_type, 
                   user_interface_type, htn_interface_type, created_at
            FROM sessions 
            ORDER BY start_time DESC
        ''')
        
        sessions = cursor.fetchall()
        
        if not sessions:
            print("No sessions found in database.")
            return
        
        print("Session Summary:")
        print("=" * 80)
        
        for session in sessions:
            session_id, start_time, end_time, env_type, ui_type, htn_type, created_at = session
            
            start_dt = datetime.fromtimestamp(start_time) if start_time else "N/A"
            end_dt = datetime.fromtimestamp(end_time) if end_time else "N/A"
            duration = end_time - start_time if start_time and end_time else "N/A"
            
            print(f"Session ID: {session_id}")
            print(f"Start Time: {start_dt}")
            print(f"End Time: {end_dt}")
            print(f"Duration: {duration} seconds" if duration != "N/A" else "Duration: N/A")
            print(f"Environment: {env_type}")
            print(f"User Interface: {ui_type}")
            print(f"HTN Interface: {htn_type}")
            print(f"Created: {created_at}")
            
            # Get event counts for this session
            cursor.execute('''
                SELECT event_type, COUNT(*) as count 
                FROM events 
                WHERE session_id = ? 
                GROUP BY event_type
            ''', (session_id,))
            
            event_counts = cursor.fetchall()
            print("Event Counts:")
            for event_type, count in event_counts:
                print(f"  {event_type}: {count}")
            
            print("-" * 80)

def view_session_events(session_id: str, db_path: str = "val/val_events.db"):
    """View all events for a specific session"""
    with sqlite3.connect(db_path) as conn:
        cursor = conn.cursor()
        cursor.execute('''
            SELECT event_type, timestamp, event_data, env_state, htn_knowledge_base
            FROM events 
            WHERE session_id = ? 
            ORDER BY timestamp
        ''', (session_id,))
        
        events = cursor.fetchall()
        
        if not events:
            print(f"No events found for session {session_id}")
            return
        
        print(f"Events for Session: {session_id}")
        print("=" * 80)
        
        for i, (event_type, timestamp, event_data, env_state, htn_kb) in enumerate(events):
            dt = datetime.fromtimestamp(timestamp)
            data = json.loads(event_data) if event_data else {}
            
            print(f"\nEvent {i+1}: {event_type}")
            print(f"Time: {dt}")
            print(f"Data: {json.dumps(data, indent=2)}")
            
            if env_state:
                env_data = json.loads(env_state)
                print(f"Environment State: {json.dumps(env_data, indent=2)}")
            
            if htn_kb:
                htn_data = json.loads(htn_kb)
                print(f"HTN Knowledge Base: {json.dumps(htn_data, indent=2)}")

def view_event_types(db_path: str = "val/val_events.db"):
    """View statistics by event type across all sessions"""
    with sqlite3.connect(db_path) as conn:
        cursor = conn.cursor()
        cursor.execute('''
            SELECT event_type, COUNT(*) as count 
            FROM events 
            GROUP BY event_type 
            ORDER BY count DESC
        ''')
        
        event_types = cursor.fetchall()
        
        if not event_types:
            print("No events found in database.")
            return
        
        print("Event Type Statistics:")
        print("=" * 40)
        
        total_events = sum(count for _, count in event_types)
        
        for event_type, count in event_types:
            percentage = (count / total_events) * 100
            print(f"{event_type}: {count} ({percentage:.1f}%)")

def view_recent_events(limit: int = 10, db_path: str = "val/val_events.db"):
    """View the most recent events"""
    with sqlite3.connect(db_path) as conn:
        cursor = conn.cursor()
        cursor.execute('''
            SELECT session_id, event_type, timestamp, event_data
            FROM events 
            ORDER BY timestamp DESC 
            LIMIT ?
        ''', (limit,))
        
        events = cursor.fetchall()
        
        if not events:
            print("No events found in database.")
            return
        
        print(f"Most Recent {limit} Events:")
        print("=" * 60)
        
        for session_id, event_type, timestamp, event_data in events:
            dt = datetime.fromtimestamp(timestamp)
            data = json.loads(event_data) if event_data else {}
            
            print(f"\nTime: {dt}")
            print(f"Session: {session_id}")
            print(f"Type: {event_type}")
            print(f"Data: {json.dumps(data, indent=2)}")

def main():
    parser = argparse.ArgumentParser(description="View VAL agent logs")
    parser.add_argument("--db", default="val/val_events.db", help="Database path")
    parser.add_argument("--summary", action="store_true", help="Show session summary")
    parser.add_argument("--session", help="View events for specific session ID")
    parser.add_argument("--types", action="store_true", help="Show event type statistics")
    parser.add_argument("--recent", type=int, default=0, help="Show N most recent events")
    
    args = parser.parse_args()
    
    if args.session:
        view_session_events(args.session, args.db)
    elif args.types:
        view_event_types(args.db)
    elif args.recent > 0:
        view_recent_events(args.recent, args.db)
    else:
        view_session_summary(args.db)

if __name__ == "__main__":
    main() 
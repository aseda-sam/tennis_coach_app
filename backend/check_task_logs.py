#!/usr/bin/env python3
"""
Check task status and logs.
"""

import sys
from pathlib import Path

# Add the app directory to the path
sys.path.insert(0, str(Path(__file__).parent))

from app.services.background_service import background_service


def check_task_logs():
    """Check task status and logs."""
    
    # Get all active tasks
    tasks = background_service.get_all_tasks()
    
    print(f"Found {len(tasks)} active tasks")
    print()
    
    for task_id, task_info in tasks.items():
        print(f"Task ID: {task_id}")
        print(f"Video ID: {task_info['video_id']}")
        print(f"Analysis Type: {task_info['analysis_type']}")
        print(f"Status: {task_info['status']}")
        print(f"Progress: {task_info['progress']}%")
        print(f"Current Stage: {task_info.get('current_stage', 'N/A')}")
        print(f"Stage Message: {task_info.get('stage_message', 'N/A')}")
        print(f"Started At: {task_info['started_at']}")
        print(f"Completed At: {task_info.get('completed_at', 'N/A')}")
        
        if task_info.get('error'):
            print(f"Error: {task_info['error']}")
        
        print("-" * 50)
        print()


if __name__ == "__main__":
    check_task_logs()

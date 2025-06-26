"""
Status Tracker Utility
Tracks and manages modification progress and status
"""

import time
import json
import threading
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, asdict
from enum import Enum


class TaskStatus(Enum):
    """Task status enumeration"""
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


@dataclass
class TaskProgress:
    """Progress information for a task"""
    task_id: str
    status: TaskStatus
    progress_percent: float = 0.0
    current_step: str = ""
    total_steps: int = 0
    completed_steps: int = 0
    start_time: float = 0.0
    end_time: Optional[float] = None
    error_message: Optional[str] = None
    result: Optional[Dict] = None
    metadata: Optional[Dict] = None


class StatusTracker:
    """
    Tracks status and progress of code modification tasks
    """
    
    def __init__(self):
        self.tasks: Dict[str, TaskProgress] = {}
        self.observers: List[callable] = []
        self.lock = threading.Lock()
        self.active_streams: Dict[str, List[callable]] = {}
    
    def create_task(self, task_id: str, total_steps: int = 1, metadata: Optional[Dict] = None) -> TaskProgress:
        """
        Create a new task for tracking
        
        Args:
            task_id: Unique identifier for the task
            total_steps: Total number of steps in the task
            metadata: Optional metadata for the task
            
        Returns:
            TaskProgress object
        """
        with self.lock:
            task = TaskProgress(
                task_id=task_id,
                status=TaskStatus.PENDING,
                total_steps=total_steps,
                start_time=time.time(),
                metadata=metadata or {}
            )
            self.tasks[task_id] = task
            self._notify_observers(task_id, task)
            return task
    
    def start_task(self, task_id: str, current_step: str = "Starting...") -> bool:
        """
        Mark task as started
        
        Args:
            task_id: Task identifier
            current_step: Description of current step
            
        Returns:
            Success status
        """
        with self.lock:
            if task_id not in self.tasks:
                return False
            
            task = self.tasks[task_id]
            task.status = TaskStatus.IN_PROGRESS
            task.current_step = current_step
            task.start_time = time.time()
            
            self._notify_observers(task_id, task)
            return True
    
    def update_progress(
        self, 
        task_id: str, 
        progress_percent: Optional[float] = None,
        current_step: Optional[str] = None,
        completed_steps: Optional[int] = None
    ) -> bool:
        """
        Update task progress
        
        Args:
            task_id: Task identifier
            progress_percent: Progress percentage (0-100)
            current_step: Description of current step
            completed_steps: Number of completed steps
            
        Returns:
            Success status
        """
        with self.lock:
            if task_id not in self.tasks:
                return False
            
            task = self.tasks[task_id]
            
            if progress_percent is not None:
                task.progress_percent = max(0, min(100, progress_percent))
            
            if current_step is not None:
                task.current_step = current_step
            
            if completed_steps is not None:
                task.completed_steps = completed_steps
                if task.total_steps > 0:
                    task.progress_percent = (completed_steps / task.total_steps) * 100
            
            self._notify_observers(task_id, task)
            return True
    
    def complete_task(self, task_id: str, result: Optional[Dict] = None) -> bool:
        """
        Mark task as completed
        
        Args:
            task_id: Task identifier
            result: Optional result data
            
        Returns:
            Success status
        """
        with self.lock:
            if task_id not in self.tasks:
                return False
            
            task = self.tasks[task_id]
            task.status = TaskStatus.COMPLETED
            task.progress_percent = 100.0
            task.end_time = time.time()
            task.current_step = "Completed"
            task.completed_steps = task.total_steps
            task.result = result
            
            self._notify_observers(task_id, task)
            return True
    
    def fail_task(self, task_id: str, error_message: str) -> bool:
        """
        Mark task as failed
        
        Args:
            task_id: Task identifier
            error_message: Error description
            
        Returns:
            Success status
        """
        with self.lock:
            if task_id not in self.tasks:
                return False
            
            task = self.tasks[task_id]
            task.status = TaskStatus.FAILED
            task.end_time = time.time()
            task.error_message = error_message
            task.current_step = f"Failed: {error_message}"
            
            self._notify_observers(task_id, task)
            return True
    
    def cancel_task(self, task_id: str) -> bool:
        """
        Cancel a task
        
        Args:
            task_id: Task identifier
            
        Returns:
            Success status
        """
        with self.lock:
            if task_id not in self.tasks:
                return False
            
            task = self.tasks[task_id]
            task.status = TaskStatus.CANCELLED
            task.end_time = time.time()
            task.current_step = "Cancelled"
            
            self._notify_observers(task_id, task)
            return True
    
    def get_task(self, task_id: str) -> Optional[TaskProgress]:
        """
        Get task progress
        
        Args:
            task_id: Task identifier
            
        Returns:
            TaskProgress object or None
        """
        with self.lock:
            return self.tasks.get(task_id)
    
    def get_all_tasks(self) -> Dict[str, TaskProgress]:
        """
        Get all tasks
        
        Returns:
            Dictionary of all tasks
        """
        with self.lock:
            return self.tasks.copy()
    
    def get_active_tasks(self) -> Dict[str, TaskProgress]:
        """
        Get active (in-progress) tasks
        
        Returns:
            Dictionary of active tasks
        """
        with self.lock:
            return {
                task_id: task for task_id, task in self.tasks.items()
                if task.status == TaskStatus.IN_PROGRESS
            }
    
    def cleanup_completed_tasks(self, older_than_hours: int = 24) -> int:
        """
        Clean up completed tasks older than specified time
        
        Args:
            older_than_hours: Remove tasks completed more than this many hours ago
            
        Returns:
            Number of tasks removed
        """
        with self.lock:
            current_time = time.time()
            cutoff_time = current_time - (older_than_hours * 3600)
            
            tasks_to_remove = []
            for task_id, task in self.tasks.items():
                if (task.status in [TaskStatus.COMPLETED, TaskStatus.FAILED, TaskStatus.CANCELLED] and
                    task.end_time and task.end_time < cutoff_time):
                    tasks_to_remove.append(task_id)
            
            for task_id in tasks_to_remove:
                del self.tasks[task_id]
            
            return len(tasks_to_remove)
    
    def add_observer(self, callback: callable):
        """
        Add observer for task updates
        
        Args:
            callback: Function to call when task updates occur
        """
        with self.lock:
            self.observers.append(callback)
    
    def remove_observer(self, callback: callable):
        """
        Remove observer
        
        Args:
            callback: Function to remove from observers
        """
        with self.lock:
            if callback in self.observers:
                self.observers.remove(callback)
    
    def _notify_observers(self, task_id: str, task: TaskProgress):
        """
        Notify all observers of task update
        
        Args:
            task_id: Task identifier
            task: Updated task progress
        """
        for observer in self.observers:
            try:
                observer(task_id, task)
            except Exception as e:
                print(f"Error notifying observer: {e}")
    
    def get_task_summary(self, task_id: str) -> Optional[Dict]:
        """
        Get task summary as dictionary
        
        Args:
            task_id: Task identifier
            
        Returns:
            Task summary dictionary or None
        """
        task = self.get_task(task_id)
        if not task:
            return None
        
        summary = asdict(task)
        summary['status'] = task.status.value
        summary['duration'] = None
        
        if task.end_time and task.start_time:
            summary['duration'] = task.end_time - task.start_time
        elif task.start_time:
            summary['duration'] = time.time() - task.start_time
        
        return summary
    
    def export_tasks(self, task_ids: Optional[List[str]] = None) -> Dict:
        """
        Export tasks to dictionary format
        
        Args:
            task_ids: Optional list of specific task IDs to export
            
        Returns:
            Dictionary containing task data
        """
        with self.lock:
            if task_ids:
                tasks_to_export = {
                    task_id: task for task_id, task in self.tasks.items()
                    if task_id in task_ids
                }
            else:
                tasks_to_export = self.tasks.copy()
            
            export_data = {
                "exported_at": time.time(),
                "tasks": {}
            }
            
            for task_id, task in tasks_to_export.items():
                export_data["tasks"][task_id] = self.get_task_summary(task_id)
            
            return export_data
    
    def get_statistics(self) -> Dict:
        """
        Get statistics about tasks
        
        Returns:
            Dictionary with task statistics
        """
        with self.lock:
            stats = {
                "total_tasks": len(self.tasks),
                "by_status": {},
                "active_tasks": 0,
                "avg_duration": 0.0,
                "success_rate": 0.0
            }
            
            completed_durations = []
            total_completed = 0
            total_failed = 0
            
            for task in self.tasks.values():
                status_key = task.status.value
                stats["by_status"][status_key] = stats["by_status"].get(status_key, 0) + 1
                
                if task.status == TaskStatus.IN_PROGRESS:
                    stats["active_tasks"] += 1
                elif task.status == TaskStatus.COMPLETED:
                    total_completed += 1
                    if task.end_time and task.start_time:
                        completed_durations.append(task.end_time - task.start_time)
                elif task.status == TaskStatus.FAILED:
                    total_failed += 1
            
            if completed_durations:
                stats["avg_duration"] = sum(completed_durations) / len(completed_durations)
            
            if total_completed + total_failed > 0:
                stats["success_rate"] = total_completed / (total_completed + total_failed)
            
            return stats


# Global status tracker instance
status_tracker = StatusTracker()
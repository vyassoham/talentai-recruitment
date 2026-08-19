from abc import ABC, abstractmethod
from typing import Callable, Any

class QueueInterface(ABC):
    @abstractmethod
    def enqueue(self, task_name: str, payload: dict) -> str:
        """Enqueue a task and return a job ID"""
        pass

    @abstractmethod
    def get_status(self, job_id: str) -> dict:
        """Get status of a job"""
        pass

class LocalSyncQueue(QueueInterface):
    """For MVP / local testing without Celery running"""
    def __init__(self):
        self.handlers = {}

    def register_handler(self, task_name: str, handler: Callable):
        self.handlers[task_name] = handler

    def enqueue(self, task_name: str, payload: dict) -> str:
        if task_name in self.handlers:
            # Run synchronously for local debug
            self.handlers[task_name](payload)
            return "sync-job-done"
        return "handler-not-found"

    def get_status(self, job_id: str) -> dict:
        return {"status": "completed"}

# In production, we'd have a CeleryQueue(QueueInterface)

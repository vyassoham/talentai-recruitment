import threading
import uuid
import time
import json
import logging
from abc import ABC, abstractmethod
from typing import Callable, Dict, Any, Optional, Set

from sqlalchemy.orm import Session
from core.database import SessionLocal
from core.config import settings
from models.all_models import BackgroundJob

logger = logging.getLogger(__name__)

# Registry for task functions across distributed workers
TASK_REGISTRY: Dict[str, Callable] = {}

def register_task(task_name: str, func: Callable):
    """Registers a named task function so workers can dynamically execute it."""
    TASK_REGISTRY[task_name] = func

class QueueInterface(ABC):
    @abstractmethod
    def enqueue(self, job_type: str, payload: dict, task_func: Callable, **kwargs) -> str:
        """Submits a job to the queue and returns the job_id."""
        pass

    @abstractmethod
    def get_status(self, job_id: str) -> Optional[Dict[str, Any]]:
        """Retrieves the status of the job from the queue."""
        pass

    @abstractmethod
    def cancel(self, job_id: str) -> bool:
        """Cancels the job. Returns True if successful."""
        pass

    @abstractmethod
    def retry(self, job_id: str, task_func: Optional[Callable] = None) -> bool:
        """Retries the job. Returns True if successfully queued."""
        pass

class LocalThreadQueue(QueueInterface):
    """
    In-memory queue using daemon threads for local development.
    Persists job state to the `BackgroundJob` table with atomic cancellation tracking.
    """
    def __init__(self):
        self._active_threads: Dict[str, threading.Thread] = {}
        self._cancelled_jobs: Set[str] = set()
        self._lock = threading.Lock()

    def enqueue(self, job_type: str, payload: dict, task_func: Callable, **kwargs) -> str:
        job_id = str(uuid.uuid4())
        
        # Automatically register task function for retryability
        register_task(job_type, task_func)
        
        # Persist Initial State
        with SessionLocal() as db:
            job = BackgroundJob(
                id=job_id,
                job_type=job_type,
                status="QUEUED",
                payload=payload
            )
            db.add(job)
            db.commit()

        # Start background thread
        thread = threading.Thread(
            target=self._run_task,
            args=(job_id, task_func, kwargs),
            daemon=True
        )
        self._active_threads[job_id] = thread
        thread.start()
        
        return job_id

    def _run_task(self, job_id: str, task_func: Callable, kwargs: dict):
        with self._lock:
            if job_id in self._cancelled_jobs:
                return

        with SessionLocal() as db:
            job = db.get(BackgroundJob, job_id)
            if not job or job.status == "CANCELLED":
                return
            
            with self._lock:
                if job_id in self._cancelled_jobs:
                    return
                    
            job.status = "PROCESSING"
            db.commit()

            try:
                result = task_func(job_id=job_id, **kwargs)
                
                with self._lock:
                    if job_id in self._cancelled_jobs:
                        return
                    
                job.status = "COMPLETED"
                job.result = result if isinstance(result, dict) else {"result": str(result)}
            except Exception as e:
                with self._lock:
                    if job_id in self._cancelled_jobs:
                        return
                logger.error(f"Job {job_id} failed: {e}", exc_info=True)
                job.status = "FAILED"
                job.error_message = str(e)
            finally:
                with self._lock:
                    if job_id not in self._cancelled_jobs:
                        db.commit()
                if job_id in self._active_threads:
                    del self._active_threads[job_id]

    def get_status(self, job_id: str) -> Optional[Dict[str, Any]]:
        with SessionLocal() as db:
            job = db.get(BackgroundJob, job_id)
            if not job:
                return None
            return {
                "id": job.id,
                "job_type": job.job_type,
                "status": job.status,
                "payload": job.payload,
                "result": job.result,
                "error": job.error_message,
                "created_at": job.created_at.isoformat(),
                "updated_at": job.updated_at.isoformat()
            }

    def cancel(self, job_id: str) -> bool:
        with self._lock:
            self._cancelled_jobs.add(job_id)

        with SessionLocal() as db:
            job = db.get(BackgroundJob, job_id)
            if not job:
                return False
                
            if job.status in ["COMPLETED", "FAILED"]:
                return False
                
            job.status = "CANCELLED"
            db.commit()
            return True

    def retry(self, job_id: str, task_func: Optional[Callable] = None) -> bool:
        with self._lock:
            if job_id in self._cancelled_jobs:
                self._cancelled_jobs.remove(job_id)

        with SessionLocal() as db:
            job = db.get(BackgroundJob, job_id)
            if not job or job.status not in ["FAILED", "CANCELLED"]:
                return False
                
            job.status = "QUEUED"
            job.retry_count = (job.retry_count or 0) + 1
            db.commit()
            
            func_to_run = task_func or TASK_REGISTRY.get(job.job_type)
            if not func_to_run:
                raise ValueError(f"No task function registered for job type '{job.job_type}'")
                
            thread = threading.Thread(
                target=self._run_task,
                args=(job_id, func_to_run, {}),
                daemon=True
            )
            self._active_threads[job_id] = thread
            thread.start()
            return True

class CeleryQueueClient(QueueInterface):
    """
    Celery + Redis distributed queue client executing background tasks
    out-of-process in standalone Celery worker pools.
    """
    def __init__(self):
        self._local_fallback = LocalThreadQueue()

    def enqueue(self, job_type: str, payload: dict, task_func: Callable, **kwargs) -> str:
        register_task(job_type, task_func)
        
        try:
            from core.celery_app import celery_app
            from services.jobs import celery_tasks
            
            job_id = str(uuid.uuid4())
            with SessionLocal() as db:
                job = BackgroundJob(
                    id=job_id,
                    job_type=job_type,
                    status="QUEUED",
                    payload=payload
                )
                db.add(job)
                db.commit()
                
            # Dispatch to appropriate Celery task
            if job_type == "CV_INGESTION":
                celery_tasks.task_cv_ingestion.apply_async(kwargs={"job_id": job_id})
            elif job_type == "ENRICHMENT_FULL":
                celery_tasks.task_full_enrichment.apply_async(kwargs={
                    "job_id": job_id, 
                    "candidate_id": kwargs.get("candidate_id") or payload.get("candidate_id")
                })
            elif job_type == "JD_PARSING":
                celery_tasks.task_jd_parsing.apply_async(kwargs={
                    "job_id": job_id, 
                    "raw_description": kwargs.get("raw_description") or payload.get("job_description")
                })
            else:
                return self._local_fallback.enqueue(job_type, payload, task_func, **kwargs)
                
            return job_id
        except Exception as e:
            logger.warning(f"Celery dispatch failed ({e}); executing via LocalThreadQueue.")
            return self._local_fallback.enqueue(job_type, payload, task_func, **kwargs)

    def get_status(self, job_id: str) -> Optional[Dict[str, Any]]:
        return self._local_fallback.get_status(job_id)

    def cancel(self, job_id: str) -> bool:
        return self._local_fallback.cancel(job_id)

    def retry(self, job_id: str, task_func: Optional[Callable] = None) -> bool:
        return self._local_fallback.retry(job_id, task_func)

def get_queue_client() -> QueueInterface:
    if settings.QUEUE_BACKEND in ["celery", "redis"]:
        return CeleryQueueClient()
    return LocalThreadQueue()

# Singleton queue client instance
queue_client = get_queue_client()

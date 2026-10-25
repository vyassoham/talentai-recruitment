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

# Registry for task functions across distributed or local workers
TASK_REGISTRY: Dict[str, Callable] = {}

def register_task(task_name: str, func: Callable):
    """Registers a named task function so workers can dynamically execute it."""
    TASK_REGISTRY[task_name] = func

def _resolve_task_func(job_type: str) -> Optional[Callable]:
    """
    Resolves task handler from in-memory registry or built-in project task handlers.
    Ensures tasks can be executed even after an application restart without prior registration.
    """
    if job_type in TASK_REGISTRY:
        return TASK_REGISTRY[job_type]
    
    if job_type == "CV_INGESTION":
        from services.jobs.ingestion_jobs import IngestionPipeline
        def run_ingestion(job_id: str, **kwargs):
            pipeline = IngestionPipeline(job_id)
            return pipeline.run()
        register_task(job_type, run_ingestion)
        return run_ingestion
        
    elif job_type in ["ENRICHMENT_FULL", "ENRICHMENT_REFRESH"]:
        from services.enrichment.web_enrichment import run_full_enrichment
        def run_enrichment(job_id: str, **kwargs):
            cand_id = kwargs.get("candidate_id")
            return run_full_enrichment(job_id=job_id, candidate_id=cand_id)
        register_task(job_type, run_enrichment)
        return run_enrichment
        
    elif job_type == "JD_PARSING":
        from services.jobs.job_service import background_process_jd
        def run_jd_parsing(job_id: str, **kwargs):
            raw_desc = kwargs.get("raw_description") or kwargs.get("job_description")
            return background_process_jd(job_id=job_id, raw_description=raw_desc)
        register_task(job_type, run_jd_parsing)
        return run_jd_parsing

    return None

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
    Persistent database-backed queue for local development and desktop execution.
    Persists job state and payload to the `BackgroundJob` table in PostgreSQL.
    Survives application restarts by recovering interrupted/orphaned tasks
    and processing them via a persistent background worker loop.
    """
    def __init__(self, autostart_worker: bool = False):
        self._active_threads: Dict[str, threading.Thread] = {}
        self._cancelled_jobs: Set[str] = set()
        self._lock = threading.Lock()
        self._wake_event = threading.Event()
        self._stop_event = threading.Event()
        self._worker_thread: Optional[threading.Thread] = None
        self._max_concurrency = 4
        
        if autostart_worker:
            self.start_worker()

    def start_worker(self):
        """Starts the persistent background queue worker and recovers orphaned jobs."""
        with self._lock:
            if self._worker_thread and self._worker_thread.is_alive():
                return
            self._stop_event.clear()
            self._worker_thread = threading.Thread(
                target=self._worker_loop,
                name="PersistentQueueWorker",
                daemon=True
            )
            self._worker_thread.start()
            logger.info("Persistent Database-Backed Queue Worker started.")

    def stop_worker(self):
        """Signals the background queue worker to stop."""
        self._stop_event.set()
        self._wake_event.set()
        if self._worker_thread and self._worker_thread.is_alive():
            self._worker_thread.join(timeout=2.0)

    def recover_orphaned_jobs(self) -> int:
        """
        Recovers jobs that were interrupted by an application restart or crash.
        Jobs in 'PROCESSING' state are safely reset to 'QUEUED' so they can be re-run.
        """
        recovered_count = 0
        try:
            with SessionLocal() as db:
                orphans = db.query(BackgroundJob).filter(BackgroundJob.status == "PROCESSING").all()
                for job in orphans:
                    logger.warning(f"Recovering orphaned job {job.id} (type: {job.job_type}) interrupted by restart.")
                    job.status = "QUEUED"
                    job.retry_count = (job.retry_count or 0) + 1
                    recovered_count += 1
                if recovered_count > 0:
                    db.commit()
                    logger.info(f"Successfully recovered {recovered_count} orphaned background jobs.")
        except Exception as e:
            logger.error(f"Error during orphaned job recovery: {e}")
        return recovered_count

    def _worker_loop(self):
        """
        Continuous background loop that monitors PostgreSQL for 'QUEUED' jobs.
        Processes jobs even across application restarts.
        """
        # Step 1: Recover any orphaned PROCESSING jobs from previous runs
        self.recover_orphaned_jobs()

        # Step 2: Poll and execute QUEUED jobs
        while not self._stop_event.is_set():
            try:
                queued_jobs = []
                with SessionLocal() as db:
                    # Query up to concurrency limit
                    queued_jobs = db.query(BackgroundJob).filter(
                        BackgroundJob.status == "QUEUED"
                    ).order_by(BackgroundJob.created_at.asc()).limit(self._max_concurrency).all()
                    
                    # Detach job metadata for thread execution
                    job_items = [
                        (j.id, j.job_type, j.payload or {}) 
                        for j in queued_jobs
                    ]

                for j_id, j_type, j_payload in job_items:
                    with self._lock:
                        if j_id in self._active_threads and self._active_threads[j_id].is_alive():
                            continue
                        if j_id in self._cancelled_jobs:
                            continue

                    func = _resolve_task_func(j_type)
                    if not func:
                        logger.warning(f"No task handler available for queued job {j_id} (type: {j_type}). Skipping.")
                        continue

                    # Extract stored kwargs if available
                    exec_kwargs = dict(j_payload.get("_kwargs", {}))
                    for k, v in j_payload.items():
                        if k != "_kwargs" and k not in exec_kwargs:
                            exec_kwargs[k] = v

                    thread = threading.Thread(
                        target=self._run_task,
                        args=(j_id, func, exec_kwargs),
                        name=f"QueueTask-{j_id[:8]}",
                        daemon=True
                    )
                    with self._lock:
                        self._active_threads[j_id] = thread
                    thread.start()

            except Exception as e:
                logger.error(f"Error in queue worker loop: {e}")

            # Wait for next wake signal or periodic 3-second heartbeat poll
            self._wake_event.wait(timeout=3.0)
            self._wake_event.clear()

    def enqueue(self, job_type: str, payload: dict, task_func: Callable, **kwargs) -> str:
        job_id = kwargs.pop("job_id", None) or str(uuid.uuid4())
        
        # Register task function for instant and retry execution
        register_task(job_type, task_func)
        
        # Serialize payload and any kwargs into combined JSON payload for persistence
        combined_payload = dict(payload) if isinstance(payload, dict) else {}
        serializable_kwargs = {}
        for k, v in kwargs.items():
            if isinstance(v, (str, int, float, bool, list, dict)) or v is None:
                serializable_kwargs[k] = v
        if serializable_kwargs:
            combined_payload["_kwargs"] = serializable_kwargs

        # Persist Initial State in PostgreSQL
        with SessionLocal() as db:
            job = BackgroundJob(
                id=job_id,
                job_type=job_type,
                status="QUEUED",
                payload=combined_payload
            )
            db.add(job)
            db.commit()

        # Immediate dispatch thread for zero-latency responsiveness
        thread = threading.Thread(
            target=self._run_task,
            args=(job_id, task_func, kwargs),
            name=f"QueueTask-{job_id[:8]}",
            daemon=True
        )
        with self._lock:
            self._active_threads[job_id] = thread
        thread.start()
        
        # Signal worker
        self._wake_event.set()
        
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
                    
                if isinstance(result, dict) and result.get("status") == "FAILED":
                    job.status = "FAILED"
                    job.error_message = result.get("error") or "Job execution failed"
                else:
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
                with self._lock:
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
                "created_at": job.created_at.isoformat() if job.created_at else None,
                "updated_at": job.updated_at.isoformat() if job.updated_at else None
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
            
            func_to_run = task_func or _resolve_task_func(job.job_type)
            if not func_to_run:
                raise ValueError(f"No task function registered for job type '{job.job_type}'")
                
            exec_kwargs = dict(job.payload.get("_kwargs", {})) if isinstance(job.payload, dict) else {}
            if isinstance(job.payload, dict):
                for k, v in job.payload.items():
                    if k != "_kwargs" and k not in exec_kwargs:
                        exec_kwargs[k] = v

            thread = threading.Thread(
                target=self._run_task,
                args=(job_id, func_to_run, exec_kwargs),
                name=f"QueueTask-{job_id[:8]}",
                daemon=True
            )
            with self._lock:
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
            
            job_id = kwargs.pop("job_id", None) or str(uuid.uuid4())
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
            elif job_type in ["ENRICHMENT_FULL", "ENRICHMENT_REFRESH"]:
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
    return LocalThreadQueue(autostart_worker=True)

# Singleton queue client instance
queue_client = get_queue_client()

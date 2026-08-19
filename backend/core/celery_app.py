import os
from celery import Celery
from core.config import settings

# Initialize Celery Application
celery_app = Celery(
    "recruitment_platform",
    broker=settings.REDIS_URL,
    backend=settings.REDIS_URL,
    include=["services.jobs.celery_tasks"]
)

# Celery Configuration for Reliability & Task Preservation
celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    task_acks_late=True, # Prevent task loss if worker terminates unexpectedly
    worker_prefetch_multiplier=1, # Ensure fair worker distribution for long-running AI jobs
    result_expires=86400, # 24 hour result retention
)

if __name__ == "__main__":
    celery_app.start()

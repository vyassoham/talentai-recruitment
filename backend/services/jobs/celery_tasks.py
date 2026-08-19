import logging
from core.celery_app import celery_app
from core.database import SessionLocal
from models.all_models import BackgroundJob

logger = logging.getLogger(__name__)

@celery_app.task(bind=True, name="tasks.cv_ingestion", max_retries=3, default_retry_delay=60)
def task_cv_ingestion(self, job_id: str, **kwargs):
    """Celery worker task for multi-stage CV document ingestion and parsing."""
    from services.jobs.ingestion_jobs import IngestionPipeline
    try:
        logger.info(f"[Celery] Starting CV ingestion for job {job_id}")
        pipeline = IngestionPipeline(job_id)
        result = pipeline.run()
        return {"status": "COMPLETED", "job_id": job_id}
    except Exception as exc:
        logger.error(f"[Celery] CV ingestion failed for job {job_id}: {exc}")
        with SessionLocal() as db:
            job = db.get(BackgroundJob, job_id)
            if job:
                job.status = "FAILED"
                job.error_message = str(exc)
                db.commit()
        raise self.retry(exc=exc)

@celery_app.task(bind=True, name="tasks.full_enrichment", max_retries=2, default_retry_delay=120)
def task_full_enrichment(self, job_id: str, candidate_id: int, **kwargs):
    """Celery worker task for open-web candidate footprint enrichment."""
    from services.enrichment.web_enrichment import run_full_enrichment
    try:
        logger.info(f"[Celery] Starting web enrichment for candidate {candidate_id}")
        return run_full_enrichment(job_id=job_id, candidate_id=candidate_id)
    except Exception as exc:
        logger.error(f"[Celery] Enrichment failed for candidate {candidate_id}: {exc}")
        raise self.retry(exc=exc)

@celery_app.task(bind=True, name="tasks.jd_parsing", max_retries=2, default_retry_delay=30)
def task_jd_parsing(self, job_id: str, raw_description: str, **kwargs):
    """Celery worker task for LLM job description extraction and embedding."""
    from services.jobs.job_service import background_process_jd
    try:
        logger.info(f"[Celery] Starting JD parsing for job {job_id}")
        return background_process_jd(job_id=job_id, raw_description=raw_description)
    except Exception as exc:
        logger.error(f"[Celery] JD parsing failed for job {job_id}: {exc}")
        raise self.retry(exc=exc)

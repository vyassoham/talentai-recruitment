from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session
from core.database import get_db
from core.queue import queue_client
from core.auth import require_role
from core.rate_limiter import rate_limit
from models.all_models import JobRequirement, User
from services.jobs.job_service import background_process_jd

router = APIRouter()

class ParseJobRequest(BaseModel):
    job_description: str = Field(
        ..., 
        min_length=10, 
        max_length=50000, 
        description="Raw Job Description text (bounded between 10 and 50,000 chars)"
    )

@router.post("/jobs/parse", status_code=status.HTTP_202_ACCEPTED)
def parse_job(
    request: ParseJobRequest, 
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("RECRUITER")),
    _rate_check = Depends(rate_limit(max_requests=15, window_seconds=60))
):
    try:
        # Enqueue the job immediately
        bg_job_id = queue_client.enqueue(
            job_type="JD_PARSING",
            payload={"job_description": request.job_description},
            task_func=background_process_jd,
            raw_description=request.job_description
        )
        return {"status": "ACCEPTED", "job_id": bg_job_id}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/jobs/{job_id}/status")
def get_job_status(
    job_id: str,
    current_user: User = Depends(require_role("RECRUITER"))
):
    job_status = queue_client.get_status(job_id)
    if not job_status:
        raise HTTPException(status_code=404, detail="Job not found")
    return job_status

@router.post("/jobs/{job_id}/cancel")
def cancel_job(
    job_id: str,
    current_user: User = Depends(require_role("RECRUITER"))
):
    success = queue_client.cancel(job_id)
    if not success:
        raise HTTPException(status_code=400, detail="Cannot cancel job (might be completed or not exist)")
    return {"status": "CANCELLED"}

@router.post("/jobs/{job_id}/retry")
def retry_job(
    job_id: str,
    current_user: User = Depends(require_role("RECRUITER"))
):
    from services.jobs.job_service import background_process_jd
    
    status_info = queue_client.get_status(job_id)
    if not status_info or status_info["status"] not in ["FAILED", "CANCELLED"]:
        raise HTTPException(status_code=400, detail="Cannot retry job (must be FAILED or CANCELLED)")
        
    def retry_wrapper(job_id_param: str, **kwargs):
        return background_process_jd(job_id=job_id_param, raw_description=status_info["payload"]["job_description"])

    success = queue_client.retry(job_id, task_func=retry_wrapper)
    if not success:
        raise HTTPException(status_code=500, detail="Failed to enqueue retry")
    return {"status": "RETRY_ACCEPTED", "job_id": job_id}

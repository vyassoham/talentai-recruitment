from fastapi import APIRouter, UploadFile, File, Depends, HTTPException, BackgroundTasks
from sqlalchemy.orm import Session
from typing import List, Optional
import uuid
import hashlib

from core.database import get_db
from core.storage import get_storage_provider
from core.security import SecurityUtils
from models.all_models import CandidateDocument, IngestionJob, User
from core.auth import get_current_user, require_role
from services.documents.validator import DocumentValidator
from services.jobs.ingestion_jobs import IngestionPipeline

router = APIRouter()
storage = get_storage_provider()

@router.post("/candidates/upload")
async def upload_cv(
    file: UploadFile = File(...), 
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("RECRUITER"))
):
    content = await file.read()
    file_hash = hashlib.sha256(content).hexdigest()
    
    # 1. Antivirus / Malware Scanning (ClamAV)
    is_clean, threat = SecurityUtils.scan_file_for_malware(content)
    if not is_clean:
        raise HTTPException(
            status_code=400, 
            detail=f"Security Violation: Malware detected in uploaded file ({threat})."
        )
    
    import tempfile
    with tempfile.TemporaryFile() as tmp:
        tmp.write(content)
        tmp.seek(0)
        
        is_valid, err = DocumentValidator.validate(tmp, file.filename)
        if not is_valid:
            raise HTTPException(status_code=400, detail=err)
            
        existing = db.query(CandidateDocument).filter(CandidateDocument.sha256_hash == file_hash).first()
        if existing:
            return {"status": "DUPLICATE", "document_id": existing.id}
            
        tmp.seek(0)
        storage_key = storage.save(tmp, file.filename)
        
    doc = CandidateDocument(
        original_filename=file.filename,
        storage_key=storage_key,
        mime_type=file.content_type,
        file_size=len(content),
        sha256_hash=file_hash
    )
    db.add(doc)
    db.flush()
    
    from core.queue import queue_client
    
    bg_job_id = str(uuid.uuid4())
    job = IngestionJob(
        id=bg_job_id,
        document_id=doc.id,
        stage="UPLOADED",
        status="QUEUED"
    )
    db.add(job)
    db.commit()
    
    def background_cv_ingestion(job_id: str, **kwargs):
        pipeline = IngestionPipeline(job_id)
        return pipeline.run()
        
    queue_client.enqueue(
        job_type="CV_INGESTION",
        payload={"filename": file.filename, "document_id": doc.id, "ingestion_job_id": bg_job_id},
        task_func=background_cv_ingestion,
        job_id=bg_job_id
    )
    
    return {
        "job_id": bg_job_id,
        "ingestion_id": bg_job_id,
        "document_id": doc.id,
        "status": "ACCEPTED"
    }

@router.get("/candidates/upload/{bg_job_id}/status")
def get_upload_status(
    bg_job_id: str,
    current_user: User = Depends(require_role("RECRUITER"))
):
    from core.queue import queue_client
    job_status = queue_client.get_status(bg_job_id)
    if not job_status:
        from core.database import SessionLocal
        with SessionLocal() as db:
            i_job = db.get(IngestionJob, bg_job_id)
            if i_job:
                return {
                    "id": i_job.id,
                    "job_type": "CV_INGESTION",
                    "status": i_job.status,
                    "stage": i_job.stage,
                    "candidate_id": None,
                    "candidate_name": None,
                    "error_message": i_job.error_message
                }
        raise HTTPException(status_code=404, detail="Job not found")

    res = job_status.get("result") or {}
    return {
        **job_status,
        "candidate_id": res.get("candidate_id"),
        "candidate_name": res.get("candidate_name"),
        "error_message": job_status.get("error") or res.get("error")
    }

@router.get("/candidates/{candidate_id}")
def get_candidate_details(
    candidate_id: int, 
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("RECRUITER"))
):
    from models.all_models import Candidate
    from services.search.retrieval import extract_candidate_sections
    
    candidate = db.get(Candidate, candidate_id)
    if not candidate:
        raise HTTPException(status_code=404, detail="Candidate not found")
        
    doc = candidate.documents[0] if candidate.documents else None
    raw_text = doc.raw_extracted_text if doc else ""
    sections = extract_candidate_sections(raw_text)
    
    cand_skills = [{"name": s.original_extracted_skill} for s in candidate.skills if s.original_extracted_skill]
    
    return {
        "candidate_id": str(candidate.id),
        "name": candidate.name,
        "email": candidate.email,
        "phone": candidate.phone,
        "location": candidate.location,
        "current_title": candidate.current_title,
        "current_company": candidate.current_company,
        "total_experience_years": candidate.total_experience_years,
        "gender": candidate.demographics.gender if candidate.demographics else None,
        "resume_url": f"{os.getenv('BACKEND_PUBLIC_URL', 'https://talentai-recruitment.onrender.com').rstrip('/')}/api/v1/candidates/{candidate.id}/resume",
        "skills": cand_skills,
        "summary": sections.get('summary', ''),
        "education": sections.get('education', []),
        "work_history": sections.get('experience', []),
        "raw_text": raw_text[:4000] if raw_text else None
    }

@router.delete("/candidates/{candidate_id}")
def delete_candidate(
    candidate_id: int, 
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("RECRUITER"))
):
    from models.all_models import Candidate, CandidateSkill, Employment, CandidateDocument, CandidateDemographics
    
    candidate = db.get(Candidate, candidate_id)
    if not candidate:
        raise HTTPException(status_code=404, detail="Candidate not found")
        
    # Delete cascade should handle relations if configured, but let's be explicit for MVP
    db.query(CandidateSkill).filter(CandidateSkill.candidate_id == candidate_id).delete()
    db.query(Employment).filter(Employment.candidate_id == candidate_id).delete()
    db.query(CandidateDemographics).filter(CandidateDemographics.candidate_id == candidate_id).delete()
    
    # Also delete recruiter feedback and evaluations
    from models.all_models import RecruiterFeedback
    db.query(RecruiterFeedback).filter(RecruiterFeedback.candidate_id == candidate_id).delete()
    from sqlalchemy import text
    db.execute(text(f"DELETE FROM evaluation_evidence WHERE candidate_id = {candidate_id}"))
    
    # Optional: Delete document from local storage (not deleting the DB record since it tracks hashes)
    doc = db.query(CandidateDocument).filter(CandidateDocument.candidate_id == candidate_id).first()
    if doc:
        if doc.storage_key:
            storage.delete(doc.storage_key)
        db.delete(doc)
        
    db.delete(candidate)
    db.commit()
    return {"status": "SUCCESS", "message": "Candidate completely erased"}

from pydantic import BaseModel, Field
from core.rate_limiter import rate_limit

class DemographicSurvey(BaseModel):
    gender: Optional[str] = Field(default=None, max_length=50)
    race_ethnicity: Optional[str] = Field(default=None, max_length=100)
    veteran_status: Optional[str] = Field(default=None, max_length=50)
    disability_status: Optional[str] = Field(default=None, max_length=50)

@router.post("/candidates/{candidate_id}/demographics")
def submit_demographics(
    candidate_id: int, 
    survey: DemographicSurvey, 
    db: Session = Depends(get_db),
    _rate_check = Depends(rate_limit(max_requests=10, window_seconds=60))
):
    from models.all_models import Candidate, CandidateDemographics
    candidate = db.get(Candidate, candidate_id)
    if not candidate:
        raise HTTPException(status_code=404, detail="Candidate not found")
        
    existing = db.query(CandidateDemographics).filter(CandidateDemographics.candidate_id == candidate_id).first()
    if existing:
        existing.gender = survey.gender
        existing.race_ethnicity = survey.race_ethnicity
        existing.veteran_status = survey.veteran_status
        existing.disability_status = survey.disability_status
    else:
        demo = CandidateDemographics(
            candidate_id=candidate_id,
            gender=survey.gender,
            race_ethnicity=survey.race_ethnicity,
            veteran_status=survey.veteran_status,
            disability_status=survey.disability_status
        )
        db.add(demo)
        
    db.commit()
    return {"status": "SUCCESS"}

@router.get("/app/version")
def get_app_version():
    """
    Returns mobile app version info for in-app OTA update checks.
    """
    return {
        "status": "SUCCESS",
        "latest_version": "1.0.1",
        "latest_version_code": 10001,
        "min_supported_version_code": 10000,
        "download_url": "https://talentai-recruiter.vercel.app/download/talentai-latest.apk",
        "release_notes": "TalentAI Mobile v1.0.1:\n- Enterprise candidate semantic search\n- Real-time AI candidate matching\n- In-app OTA updates\n- Offline resilience & instant resume viewing",
        "mandatory": False,
        "published_at": "2026-10-27T00:00:00Z"
    }


from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from typing import List, Optional
from sqlalchemy.orm import Session

from core.database import get_db
from core.auth import require_role
from core.rate_limiter import rate_limit
from models.all_models import User

router = APIRouter()

# ==================== Passive Sourcing Endpoints ====================

class GitHubSourceRequest(BaseModel):
    language: str = Field(..., min_length=1, max_length=100)
    location: Optional[str] = Field(default=None, max_length=200)
    min_repos: int = Field(default=5, ge=0, le=1000)
    max_results: int = Field(default=20, ge=1, le=100)

class StackOverflowSourceRequest(BaseModel):
    tags: List[str] = Field(..., min_length=1, max_length=10)
    min_reputation: int = Field(default=1000, ge=0, le=1000000)
    max_results: int = Field(default=20, ge=1, le=100)

@router.post("/sourcing/github")
def source_from_github(
    request: GitHubSourceRequest,
    current_user: User = Depends(require_role("RECRUITER")),
    _rate_check = Depends(rate_limit(max_requests=10, window_seconds=60))
):
    """
    Actively searches GitHub for developers matching a skill/location profile.
    Discovers passive candidates who haven't applied yet.
    """
    from services.enrichment.passive_sourcer import PassiveSourcer
    
    discovered = PassiveSourcer.search_github(
        language=request.language,
        location=request.location,
        min_repos=request.min_repos,
        max_results=request.max_results
    )
    
    if not discovered:
        return {"status": "NO_RESULTS", "candidates_found": 0}
    
    # Ingest them into our database
    result = PassiveSourcer.ingest_discovered_candidates(discovered)
    
    return {
        "status": "SUCCESS",
        "candidates_discovered": len(discovered),
        "candidates_created": result["created"],
        "duplicates_skipped": result["skipped_duplicates"]
    }

@router.post("/sourcing/stackoverflow")
def source_from_stackoverflow(
    request: StackOverflowSourceRequest,
    current_user: User = Depends(require_role("RECRUITER")),
    _rate_check = Depends(rate_limit(max_requests=10, window_seconds=60))
):
    """
    Searches StackOverflow for top answerers in specific technology tags.
    """
    from services.enrichment.passive_sourcer import PassiveSourcer
    
    discovered = PassiveSourcer.search_stackoverflow(
        tags=request.tags,
        min_reputation=request.min_reputation,
        max_results=request.max_results
    )
    
    if not discovered:
        return {"status": "NO_RESULTS", "candidates_found": 0}
    
    result = PassiveSourcer.ingest_discovered_candidates(discovered)
    
    return {
        "status": "SUCCESS",
        "candidates_discovered": len(discovered),
        "candidates_created": result["created"],
        "duplicates_skipped": result["skipped_duplicates"]
    }

# ==================== Staleness & Refresh Endpoints ====================

@router.get("/sourcing/stale-profiles")
def get_stale_profiles(
    threshold_days: int = Query(default=90, ge=1, le=3650, description="Profiles older than this many days are considered stale"),
    limit: int = Query(default=50, ge=1, le=500, description="Maximum number of stale profiles to return"),
    current_user: User = Depends(require_role("RECRUITER"))
):
    """
    Returns candidates whose profiles are stale and need refreshing.
    """
    from services.enrichment.staleness_checker import get_stale_candidates
    
    stale = get_stale_candidates(threshold_days=threshold_days, limit=limit)
    return {"stale_profiles": stale, "total": len(stale)}

@router.post("/sourcing/refresh-stale")
def trigger_stale_refresh(
    threshold_days: int = Query(default=90, ge=1, le=3650),
    limit: int = Query(default=20, ge=1, le=200),
    current_user: User = Depends(require_role("RECRUITER"))
):
    """
    Enqueues background jobs to re-enrich stale candidate profiles.
    This refreshes their GitHub, StackOverflow, and Scholar data.
    """
    from services.enrichment.staleness_checker import refresh_stale_profiles
    
    result = refresh_stale_profiles(threshold_days=threshold_days, limit=limit)
    return {"status": "REFRESH_INITIATED", **result}

@router.post("/sourcing/enrich/{candidate_id}")
def trigger_manual_enrichment(
    candidate_id: int, 
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("RECRUITER")),
    _rate_check = Depends(rate_limit(max_requests=15, window_seconds=60))
):
    """
    Manually triggers full enrichment for a specific candidate.
    Runs GitHub audit, StackOverflow check, Google Scholar check, and Design portfolio check.
    """
    from models.all_models import Candidate
    from core.queue import queue_client
    from services.enrichment.web_enrichment import run_full_enrichment
    
    candidate = db.get(Candidate, candidate_id)
    if not candidate:
        raise HTTPException(status_code=404, detail="Candidate not found")
    
    job_id = queue_client.enqueue(
        job_type="ENRICHMENT_FULL",
        payload={"candidate_id": candidate_id},
        task_func=run_full_enrichment,
        candidate_id=candidate_id
    )
    
    return {"status": "ENRICHMENT_QUEUED", "job_id": job_id, "candidate_id": candidate_id}

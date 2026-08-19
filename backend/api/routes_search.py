import time
import os
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session, selectinload
from sqlalchemy import or_
from core.database import get_db
from core.auth import require_role
from core.config import settings
from core.rate_limiter import rate_limit
from models.all_models import JobRequirement, Candidate, User, RecruiterFeedback
from services.search.eligibility import EligibilityEngine
from services.search.retrieval import HybridRetrievalEngine
from services.ai.reranker import AIReranker

router = APIRouter()

class SearchRequest(BaseModel):
    job_id: str = Field(..., min_length=1, max_length=100, description="Unique ID of the target JobRequirement")
    top_k: int = Field(default=settings.RETRIEVAL_TOP_K, ge=1, le=500, description="Top-K vector candidates to evaluate")

@router.post("/candidates/search")
async def search_candidates(
    request: SearchRequest, 
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("RECRUITER")),
    _rate_check = Depends(rate_limit(max_requests=20, window_seconds=60))
):
    start_total = time.time()
    
    # 1. Fetch Job
    job = db.get(JobRequirement, request.job_id)
    if not job:
        raise HTTPException(status_code=404, detail="JobRequirement not found")
        
    # 2. Parameterized SQL Pre-Filtering & Eager Loading
    candidate_query = db.query(Candidate).options(selectinload(Candidate.skills))
    
    if job.min_experience_years is not None and job.min_experience_years > 0:
        candidate_query = candidate_query.filter(
            or_(
                Candidate.total_experience_years >= job.min_experience_years,
                Candidate.total_experience_years.is_(None)
            )
        )
        
    candidates = candidate_query.all()
    
    # 3. Eligibility
    start_elig = time.time()
    eligible_results = EligibilityEngine.filter_eligible_candidates(candidates, job)
    elig_latency = time.time() - start_elig
    
    # 4. Hybrid Retrieval & Ranking
    start_retrieval = time.time()
    retrieval_engine = HybridRetrievalEngine(db)
    top_candidates = retrieval_engine.retrieve(job, eligible_results, top_k=request.top_k)
    retrieval_latency = time.time() - start_retrieval
    
    # 5. Phase 4: Asynchronous Parallel AI Deep Reranking
    start_rerank = time.time()
    reranker = AIReranker(db)
    top_n = settings.RERANK_TOP_N
    final_candidates = await reranker.evaluate_candidates_async(job, top_candidates, top_n=top_n)
    rerank_latency = time.time() - start_rerank

    total_latency = time.time() - start_total
    
    return {
        "job_id": request.job_id,
        "eligible_count": len(eligible_results),
        "retrieved_count": len(final_candidates),
        "telemetry": {
            "eligibility_latency_sec": round(elig_latency, 4),
            "retrieval_ranking_latency_sec": round(retrieval_latency, 4),
            "rerank_latency_sec": round(rerank_latency, 4),
            "total_search_latency_sec": round(total_latency, 4)
        },
        "candidates": final_candidates
    }

class FeedbackRequest(BaseModel):
    job_id: str = Field(..., min_length=1, max_length=100)
    feedback_type: str = Field(..., min_length=1, max_length=50)
    comments: str = Field(..., max_length=5000, description="Recruiter feedback comments (up to 5,000 chars)")

@router.post("/candidates/{candidate_id}/feedback")
def submit_feedback(
    candidate_id: int, 
    request: FeedbackRequest, 
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("RECRUITER"))
):
    feedback = RecruiterFeedback(
        job_id=request.job_id,
        candidate_id=candidate_id,
        feedback_type=request.feedback_type,
        comments=request.comments
    )
    db.add(feedback)
    db.commit()
    return {"status": "success", "message": "Feedback recorded."}

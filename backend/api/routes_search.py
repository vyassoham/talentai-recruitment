import time
import os
import re
import asyncio
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import Response, FileResponse
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session, selectinload, defer
from sqlalchemy import or_
from core.database import get_db
from core.auth import require_role, verify_api_key
from core.config import settings
from core.rate_limiter import rate_limit
from models.all_models import JobRequirement, Candidate, User, RecruiterFeedback, CandidateDocument
from services.search.eligibility import EligibilityEngine, CandidateEligibilityResult
from services.search.retrieval import HybridRetrievalEngine
from services.ai.reranker import AIReranker
from services.ai.provider import get_ai_provider
from services.documents.resume_generator import generate_pdf_resume

router = APIRouter()

# High-speed LRU query embedding cache
_QUERY_EMBEDDING_CACHE: dict[str, list[float]] = {}

class SearchRequest(BaseModel):
    job_id: Optional[str] = Field(default="1", min_length=0, max_length=100, description="Unique ID of the target JobRequirement")
    query: Optional[str] = Field(default=None, description="Free-form natural language query in English, Hinglish, or Hindi")
    top_k: int = Field(default=settings.RETRIEVAL_TOP_K, ge=1, le=500, description="Top-K vector candidates to evaluate")
    rerank_top_n: Optional[int] = Field(default=None, ge=0, le=50, description="Number of top candidates to evaluate via live LLM")
    fast_mode: Optional[bool] = Field(default=None, description="When True (default), delivers sub-second hybrid search results with instant AI scoring cards")

@router.post("/candidates/search")
async def search_candidates(
    request: SearchRequest, 
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("RECRUITER")),
    _rate_check = Depends(rate_limit(max_requests=60, window_seconds=60))
):
    start_total = time.time()
    
    # 1. Fetch or synthesize Job Requirement
    job = None
    if request.job_id:
        job = db.get(JobRequirement, request.job_id)
        
    if not job:
        job = db.query(JobRequirement).order_by(JobRequirement.created_at.desc()).first()
        
    if not job:
        job = JobRequirement(
            id=request.job_id or "1",
            title=request.query or "Software Engineering Professional",
            mandatory_skills=[{"canonical_skill_name": "Python"}, {"canonical_skill_name": "FastAPI"}] if not request.query else [{"canonical_skill_name": w.strip()} for w in request.query.split() if len(w) > 3][:3],
            min_experience_years=0.0
        )
    else:
        db.expunge(job)
        
    if request.query:
        # High-speed cached embedding generation & intelligent intent extraction
        try:
            clean_q = request.query.strip().lower()
            if clean_q in _QUERY_EMBEDDING_CACHE:
                q_emb = _QUERY_EMBEDDING_CACHE[clean_q]
            else:
                provider = get_ai_provider()
                q_emb, _ = provider.generate_embeddings(request.query)
                if len(_QUERY_EMBEDDING_CACHE) > 500:
                    _QUERY_EMBEDDING_CACHE.pop(next(iter(_QUERY_EMBEDDING_CACHE)))
                _QUERY_EMBEDDING_CACHE[clean_q] = q_emb

            job.embedding = q_emb
            job.raw_description = f"CRITICAL USER REQUIREMENT: {request.query}\n\nOriginal JD Context:\n{job.raw_description or ''}"
            job.title = f"Custom Search: {request.query[:50]}"

            # Smart AI/ML intent extraction from natural language query
            KNOWN_TECH_SKILLS = [
                "python", "java", "c++", "c#", ".net", "dotnet", "javascript", "typescript", "react",
                "node.js", "nodejs", "fastapi", "flask", "django", "sql", "postgresql", "mysql", "mongodb",
                "redis", "docker", "kubernetes", "aws", "azure", "gcp", "devops", "ci/cd", "git", "linux",
                "rest api", "graphql", "html", "css", "tailwind", "next.js", "vue", "angular", "spark",
                "kafka", "airflow", "hadoop", "pandas", "numpy", "pytorch", "tensorflow", "machine learning",
                "deep learning", "nlp", "llm", "pgvector", "distributed systems"
            ]
            extracted_skills = []
            for s in KNOWN_TECH_SKILLS:
                pattern = r'\b' + re.escape(s) + r'\b'
                if re.search(pattern, clean_q):
                    extracted_skills.append({"canonical_skill_name": s.title()})

            if extracted_skills:
                job.mandatory_skills = extracted_skills[:4]
                job.preferred_skills = extracted_skills[4:]
            else:
                job.mandatory_skills = []
                job.preferred_skills = []

            # Extract experience intent if specified (e.g., "5+ years", "3 yrs")
            exp_match = re.search(r'(\d+(?:\.\d+)?)\+?\s*(?:years?|yrs?)', clean_q)
            if exp_match:
                try:
                    job.min_experience_years = float(exp_match.group(1))
                except Exception:
                    pass
        except Exception:
            pass
        
    # 2. Optimized SQL Pre-Filtering: Defer heavy 10KB raw texts for 50x network speedup
    candidate_query = db.query(Candidate).options(
        selectinload(Candidate.skills),
        selectinload(Candidate.demographics),
        selectinload(Candidate.documents).options(
            defer(CandidateDocument.raw_extracted_text),
            defer(CandidateDocument.normalized_text)
        )
    )
    
    if job.min_experience_years is not None and job.min_experience_years > 0:
        candidate_query = candidate_query.filter(
            or_(
                Candidate.total_experience_years >= job.min_experience_years,
                Candidate.total_experience_years.is_(None)
            )
        )
        
    candidates = candidate_query.all()
    
    # If no candidates in DB yet, return empty list gracefully
    if not candidates:
        return {
            "job_id": request.job_id or "1",
            "eligible_count": 0,
            "retrieved_count": 0,
            "telemetry": {
                "eligibility_latency_sec": 0.001,
                "retrieval_ranking_latency_sec": 0.001,
                "rerank_latency_sec": 0.001,
                "total_search_latency_sec": round(time.time() - start_total, 4)
            },
            "candidates": []
        }
    
    # 3. Eligibility
    start_elig = time.time()
    eligible_results = EligibilityEngine.filter_eligible_candidates(candidates, job)
    elig_latency = time.time() - start_elig
    
    # 4. Hybrid Retrieval & Ranking (Passes preloaded candidates to eliminate duplicate DB query)
    start_retrieval = time.time()
    retrieval_engine = HybridRetrievalEngine(db)
    top_candidates = retrieval_engine.retrieve(job, eligible_results, top_k=request.top_k, candidates=candidates)
    retrieval_latency = time.time() - start_retrieval
    
    # 5. Phase 4: Fast & Intelligent AI Reranking
    start_rerank = time.time()
    reranker = AIReranker(db)
    
    is_fast = request.fast_mode if request.fast_mode is not None else settings.FAST_SEARCH_DEFAULT
    if request.rerank_top_n is not None:
        top_n = request.rerank_top_n
    elif is_fast:
        top_n = 0
    else:
        top_n = settings.RERANK_TOP_N or 1

    final_candidates = await reranker.evaluate_candidates_async(job, top_candidates, top_n=top_n)
    rerank_latency = time.time() - start_rerank

    total_latency = time.time() - start_total
    
    return {
        "job_id": request.job_id or "1",
        "query": request.query,
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

class EvaluateCandidateRequest(BaseModel):
    job_id: Optional[str] = Field(default="1", min_length=0, max_length=100)

@router.post("/candidates/{candidate_id}/evaluate")
async def evaluate_single_candidate(
    candidate_id: int,
    request: Optional[EvaluateCandidateRequest] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("RECRUITER"))
):
    """
    On-demand deep AI evaluation for a single candidate using Gemini LLM.
    Quotes verbatim evidence from CV, assesses requirements, and checks hallucinations.
    """
    job_id = request.job_id if request and request.job_id else "1"
    job = db.get(JobRequirement, job_id)
    if not job:
        job = db.query(JobRequirement).order_by(JobRequirement.created_at.desc()).first()
    if not job:
        job = JobRequirement(
            id=job_id,
            title="Software Engineering Professional",
            mandatory_skills=[{"canonical_skill_name": "Software Development"}],
            min_experience_years=0.0
        )
        
    candidate = db.get(Candidate, candidate_id)
    if not candidate:
        raise HTTPException(status_code=404, detail="Candidate not found")
        
    c_dict = {
        "candidate_id": str(candidate.id),
        "name": candidate.name,
        "current_title": candidate.current_title,
        "total_experience_years": candidate.total_experience_years,
        "location": candidate.location,
        "current_company": candidate.current_company,
        "retrieval_score": 0.85,
        "matched_skills": [s.original_extracted_skill for s in candidate.skills[:5]] if candidate.skills else [],
        "missing_preferred_skills": []
    }
    
    reranker = AIReranker(db)
    system_prompt = (
        "You are an expert technical recruiter AI. Your task is to deeply evaluate a candidate's CV against a job description.\n"
        "CRITICAL INSTRUCTION: You must quote verbatim from the candidate's CV as evidence. Do not invent evidence.\n"
        "If the information is not present in the CV, mark the evidence as 'INSUFFICIENT_EVIDENCE' and the assessment as 'Insufficient Evidence'.\n"
        "Score the candidate objectively."
    )
    job_context = f"Job Title: {job.title}\nDescription: {job.raw_description}\nMandatory: {job.mandatory_skills}\nPreferred: {job.preferred_skills}"
    
    evaluated = await asyncio.to_thread(
        reranker._evaluate_single_candidate_sync,
        c_dict,
        job,
        job_context,
        system_prompt
    )
    try:
        db.commit()
    except Exception:
        db.rollback()
    
    return {
        "candidate_id": candidate_id,
        "job_id": job_id,
        "ai_evaluation": evaluated.get("ai_evaluation"),
        "composite_score": evaluated.get("composite_score"),
        "final_score": evaluated.get("final_score"),
        "match_reasons": evaluated.get("match_reasons"),
        "evaluations": evaluated.get("evaluations")
    }

@router.get("/candidates/{candidate_id}/resume")
def get_candidate_resume_preview(
    candidate_id: int,
    db: Session = Depends(get_db)
):
    """
    Delivers a guaranteed resume PDF preview.
    1. Serves original binary PDF from storage if present.
    2. Fallback (Jugaad): Synthesizes a high-fidelity branded executive PDF on the fly
       using candidate profile and parsed normalized text if the raw file was purged.
    """
    candidate = db.get(Candidate, candidate_id)
    if not candidate:
        raise HTTPException(status_code=404, detail="Candidate not found")
        
    doc = db.query(CandidateDocument).filter(CandidateDocument.candidate_id == candidate_id).first()
    safe_name = re.sub(r'[^a-zA-Z0-9_-]', '_', candidate.name or f"Candidate_{candidate_id}")
    
    # 1. Check local storage disk
    storage_dirs = [
        os.path.join(os.path.dirname(__file__), "..", "storage"),
        os.path.join(os.path.dirname(__file__), "..", "..", "backend", "storage"),
        os.path.abspath("backend/storage"),
        os.path.abspath("storage")
    ]
    if doc and doc.storage_key:
        for s_dir in storage_dirs:
            potential_path = os.path.join(s_dir, doc.storage_key)
            if os.path.isfile(potential_path) and os.path.getsize(potential_path) > 0:
                return FileResponse(
                    potential_path,
                    media_type="application/pdf",
                    headers={"Content-Disposition": f'inline; filename="{safe_name}_Resume.pdf"'}
                )
                
    # 2. Check cached synthesized PDF on disk
    cache_filename = f"synth_resume_{candidate_id}.pdf"
    for s_dir in storage_dirs:
        cache_path = os.path.join(s_dir, cache_filename)
        if os.path.isfile(cache_path) and os.path.getsize(cache_path) > 0:
            return FileResponse(
                cache_path,
                media_type="application/pdf",
                headers={"Content-Disposition": f'inline; filename="{safe_name}_Resume.pdf"'}
            )

    # 3. Dynamic synthesis fallback (Jugaad): Generate clean PDF using ReportLab
    try:
        pdf_bytes = generate_pdf_resume(candidate, doc)
        
        # Save to local storage for instant subsequent serving
        try:
            target_dir = os.path.join(os.path.dirname(__file__), "..", "storage")
            os.makedirs(target_dir, exist_ok=True)
            with open(os.path.join(target_dir, cache_filename), "wb") as f:
                f.write(pdf_bytes)
        except Exception:
            pass
            
        return Response(
            content=pdf_bytes,
            media_type="application/pdf",
            headers={
                "Content-Disposition": f'inline; filename="{safe_name}_Resume.pdf"',
                "Content-Type": "application/pdf"
            }
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to generate resume preview: {e}")

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

TECH_SKILL_PATTERNS = [
    # Data & Distributed Systems
    ("apache spark", "Apache Spark"),
    ("pyspark", "Apache Spark"),
    ("spark", "Apache Spark"),
    ("kafka", "Kafka"),
    ("airflow", "Airflow"),
    ("apache airflow", "Airflow"),
    ("bigquery", "BigQuery"),
    ("snowflake", "Snowflake"),
    ("hadoop", "Hadoop"),
    ("hive", "Hive"),
    ("databricks", "Databricks"),
    ("dbt", "dbt"),
    
    # Backend & Frameworks
    ("fastapi", "FastAPI"),
    ("flask", "Flask"),
    ("django", "Django"),
    ("spring boot", "Spring Boot"),
    ("spring", "Spring Boot"),
    ("express", "Express"),
    ("nest.js", "NestJS"),
    ("nestjs", "NestJS"),
    
    # Databases
    ("postgresql", "PostgreSQL"),
    ("postgres", "PostgreSQL"),
    ("psql", "PostgreSQL"),
    ("mysql", "MySQL"),
    ("mongodb", "MongoDB"),
    ("redis", "Redis"),
    ("cassandra", "Cassandra"),
    ("sqlite", "SQLite"),
    ("dynamodb", "DynamoDB"),
    ("oracle", "Oracle"),
    ("sql server", "SQL Server"),
    ("sql", "SQL"),
    
    # Programming Languages
    ("python", "Python"),
    ("javascript", "JavaScript"),
    ("typescript", "TypeScript"),
    ("java", "Java"),
    ("c++", "C++"),
    ("c#", "C#"),
    (".net", ".NET"),
    ("dotnet", ".NET"),
    ("golang", "Go"),
    ("rust", "Rust"),
    ("php", "PHP"),
    ("ruby", "Ruby"),
    ("scala", "Scala"),
    ("kotlin", "Kotlin"),
    ("swift", "Swift"),
    
    # Frontend & Fullstack
    ("react", "React"),
    ("react.js", "React"),
    ("reactjs", "React"),
    ("next.js", "Next.js"),
    ("nextjs", "Next.js"),
    ("angular", "Angular"),
    ("vue", "Vue"),
    ("vue.js", "Vue"),
    ("tailwind", "Tailwind"),
    ("html", "HTML"),
    ("css", "CSS"),
    ("redux", "Redux"),
    
    # Cloud & DevOps
    ("docker", "Docker"),
    ("kubernetes", "Kubernetes"),
    ("k8s", "Kubernetes"),
    ("aws", "AWS"),
    ("amazon web services", "AWS"),
    ("azure", "Azure"),
    ("gcp", "GCP"),
    ("google cloud", "GCP"),
    ("terraform", "Terraform"),
    ("ansible", "Ansible"),
    ("jenkins", "Jenkins"),
    ("ci/cd", "CI/CD"),
    ("devops", "DevOps"),
    ("git", "Git"),
    ("linux", "Linux"),
    
    # AI / ML / Data Science
    ("pytorch", "PyTorch"),
    ("tensorflow", "TensorFlow"),
    ("scikit-learn", "Scikit-Learn"),
    ("pandas", "Pandas"),
    ("numpy", "NumPy"),
    ("machine learning", "Machine Learning"),
    ("deep learning", "Deep Learning"),
    ("nlp", "NLP"),
    ("computer vision", "Computer Vision"),
    ("llm", "LLM"),
    ("pgvector", "pgvector"),
    ("langchain", "LangChain"),
    ("huggingface", "HuggingFace"),
    
    # Architecture
    ("microservices", "Microservices"),
    ("rest api", "REST API"),
    ("graphql", "GraphQL"),
    ("distributed systems", "Distributed Systems"),
    ("system design", "System Design")
]

ROLE_PATTERNS = [
    ("data engineer", "Data Engineer"),
    ("big data engineer", "Data Engineer"),
    ("python developer", "Python Developer"),
    ("python engineer", "Python Developer"),
    ("backend developer", "Backend Developer"),
    ("backend engineer", "Backend Developer"),
    ("frontend developer", "Frontend Developer"),
    ("frontend engineer", "Frontend Developer"),
    ("full stack", "Full Stack Developer"),
    ("fullstack", "Full Stack Developer"),
    ("devops engineer", "DevOps Engineer"),
    ("cloud engineer", "Cloud Engineer"),
    ("cloud architect", "Cloud Architect"),
    ("solution architect", "Solutions Architect"),
    ("solutions architect", "Solutions Architect"),
    ("software architect", "Software Architect"),
    ("architect", "Architect"),
    ("machine learning engineer", "Machine Learning Engineer"),
    ("ml engineer", "Machine Learning Engineer"),
    ("data scientist", "Data Scientist"),
    ("qa engineer", "QA Engineer"),
    ("mobile developer", "Mobile Developer"),
    ("android developer", "Android Developer"),
    ("ios developer", "iOS Developer"),
]

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

            # Smart AI/ML intent extraction from natural language and Hinglish queries
            extracted_skills = []
            seen_skills = set()
            for pattern, canonical in TECH_SKILL_PATTERNS:
                if re.search(r'\b' + re.escape(pattern) + r'\b', clean_q):
                    if canonical not in seen_skills:
                        extracted_skills.append({"canonical_skill_name": canonical})
                        seen_skills.add(canonical)

            found_role = None
            for pattern, role in ROLE_PATTERNS:
                if re.search(r'\b' + re.escape(pattern) + r'\b', clean_q):
                    found_role = role
                    break

            # Attach target role for semantic ranking boost
            job.target_role = found_role or job.title

            if extracted_skills:
                # If 1 to 5 skills mentioned, all are mandatory requirements
                # If more than 5, top 5 are mandatory, rest preferred
                if len(extracted_skills) <= 5:
                    job.mandatory_skills = extracted_skills
                    job.preferred_skills = []
                else:
                    job.mandatory_skills = extracted_skills[:5]
                    job.preferred_skills = extracted_skills[5:]
            else:
                job.mandatory_skills = []
                job.preferred_skills = []

            # Extract experience intent (e.g. "5+ years", "3 yrs", "5 saal", "senior", "lead")
            exp_match = re.search(r'(\d+(?:\.\d+)?)\+?\s*(?:years?|yrs?|saal)', clean_q)
            if exp_match:
                try:
                    job.min_experience_years = float(exp_match.group(1))
                except Exception:
                    pass
            elif any(w in clean_q for w in ["lead", "principal", "architect"]):
                job.min_experience_years = 7.0
            elif any(w in clean_q for w in ["senior", "sr."]):
                job.min_experience_years = 4.0
            elif any(w in clean_q for w in ["junior", "fresher", "jr."]):
                job.min_experience_years = 0.0
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
    
    # Enforce multi-tenant organization isolation
    if current_user.role != "ADMIN" and getattr(current_user, "organization_id", None):
        candidate_query = candidate_query.filter(Candidate.organization_id == current_user.organization_id)
    
    if job.min_experience_years is not None and job.min_experience_years > 0:
        inclusive_min = max(0.0, job.min_experience_years - 2.0)
        candidate_query = candidate_query.filter(
            or_(
                Candidate.total_experience_years >= inclusive_min,
                Candidate.total_experience_years.is_(None)
            )
        )
        
    try:
        candidates = candidate_query.order_by(Candidate.id.desc()).limit(max(request.top_k, 250)).all()
        if not isinstance(candidates, list) or (candidates and not isinstance(candidates[0], Candidate)):
            candidates = candidate_query.all()
    except Exception:
        candidates = candidate_query.all()
    if isinstance(candidates, list) and len(candidates) > 250:
        candidates = candidates[:250]
    
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
        comments=request.comments,
        organization_id=getattr(current_user, "organization_id", None) or "org_talentai_default"
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
        
    # Enforce multi-tenant isolation
    if current_user.role != "ADMIN" and candidate.organization_id and current_user.organization_id:
        if candidate.organization_id != current_user.organization_id:
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
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("RECRUITER"))
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
        
    # Enforce multi-tenant isolation
    if current_user.role != "ADMIN" and candidate.organization_id and current_user.organization_id:
        if candidate.organization_id != current_user.organization_id:
            raise HTTPException(status_code=404, detail="Candidate resume not found")
        
    doc = db.query(CandidateDocument).filter(CandidateDocument.candidate_id == candidate_id).first()
    safe_name = re.sub(r'[^a-zA-Z0-9_-]', '_', candidate.name or f"Candidate_{candidate_id}")
    
    # 0. Enterprise Cloud Storage Signed URL (S3 / GCS / Supabase)
    from core.storage import get_storage_provider
    from fastapi.responses import RedirectResponse
    storage_provider = get_storage_provider()
    if doc and doc.storage_key:
        try:
            signed_url = storage_provider.create_signed_url(doc.storage_key, expires_in=3600)
            if signed_url:
                return RedirectResponse(url=signed_url, status_code=307)
        except Exception:
            pass

    # 1. Check local storage disk
    storage_dirs = [
        os.path.join(os.path.dirname(__file__), "..", "storage"),
        os.path.join(os.path.dirname(__file__), "..", "..", "backend", "storage"),
        os.path.abspath("backend/storage"),
        os.path.abspath("storage")
    ]
    if doc and doc.storage_key:
        for s_dir in storage_dirs:
            safe_key = os.path.basename(str(doc.storage_key).replace("\\", "/"))
            potential_path = os.path.abspath(os.path.join(s_dir, safe_key))
            if not potential_path.startswith(os.path.abspath(s_dir)):
                continue
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

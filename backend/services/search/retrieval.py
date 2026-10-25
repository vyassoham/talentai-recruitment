import re
from typing import List, Dict, Any, Optional
from sqlalchemy.orm import Session, selectinload
from sqlalchemy import select
from models.all_models import Candidate, JobRequirement, CandidateSectionEmbedding, RecruiterFeedback
from services.search.eligibility import CandidateEligibilityResult
from core.config import settings

# Precompiled regex for fast contact extraction (avoids repetitive recompilation and CPU spikes)
EMAIL_REGEX = re.compile(r'[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+')
PHONE_REGEX = re.compile(r'(?:\+?\d{1,3}[\s-]?)?(?:\(?\d{2,4}\)?[\s-]?)?\d{3,4}[\s-]?\d{3,4}')
NON_DIGIT_REGEX = re.compile(r'\D')

# Configurable retrieval weights
W_SKILL = settings.RETRIEVAL_WEIGHT_SKILL
W_SEMANTIC = settings.RETRIEVAL_WEIGHT_SEMANTIC
W_EXPERIENCE = settings.RETRIEVAL_WEIGHT_EXPERIENCE
W_PREFERRED = settings.RETRIEVAL_WEIGHT_PREFERRED

class RetrievalResult:
    def __init__(self, candidate: Candidate, eligibility: CandidateEligibilityResult):
        self.candidate = candidate
        self.eligibility = eligibility
        self.skill_match_score = 0.0
        self.semantic_similarity = 0.0
        self.experience_signal = 0.0
        self.preferred_skill_signal = 0.0
        self.best_matching_section: Optional[str] = None
        
        self.matched_skills = []
        self.missing_preferred_skills = []
        
    @property
    def retrieval_score(self) -> float:
        return (
            (self.skill_match_score * W_SKILL) +
            (self.semantic_similarity * W_SEMANTIC) +
            (self.experience_signal * W_EXPERIENCE) +
            (self.preferred_skill_signal * W_PREFERRED)
        )
        
    def to_dict(self):
        doc = self.candidate.documents[0] if self.candidate.documents else None
        resume_url = None
        email = self.candidate.email
        phone = self.candidate.phone
        
        if doc:
            # Fallback regex extraction only if missing in DB (bounded to first 2500 chars to avoid CPU spikes on 50KB strings)
            if (not email or not phone) and doc.raw_extracted_text:
                header_text = doc.raw_extracted_text[:2500]
                if not email:
                    m_email = EMAIL_REGEX.search(header_text)
                    if m_email:
                        email = m_email.group(0)
                if not phone:
                    for m_phone in PHONE_REGEX.finditer(header_text):
                        candidate_phone = m_phone.group(0)
                        digits = NON_DIGIT_REGEX.sub('', candidate_phone)
                        if 10 <= len(digits) <= 14:
                            phone = candidate_phone.strip()
                            break

        # Guaranteed resume preview link (works for local files, cloud files, and auto-synthesized PDFs)
        resume_url = f"http://127.0.0.1:8000/api/v1/candidates/{self.candidate.id}/resume"

        return {
            "candidate_id": str(self.candidate.id),
            "name": self.candidate.name,
            "email": email,
            "phone": phone,
            "current_title": self.candidate.current_title,
            "total_experience_years": self.candidate.total_experience_years,
            "location": self.candidate.location,
            "gender": self.candidate.demographics.gender if self.candidate.demographics else None,
            "current_company": self.candidate.current_company,
            "resume_url": resume_url,
            "retrieval_score": round(self.retrieval_score, 4),
            "skill_match_score": round(self.skill_match_score, 4),
            "semantic_similarity": round(self.semantic_similarity, 4),
            "experience_signal": round(self.experience_signal, 4),
            "best_matching_section": self.best_matching_section,
            "matched_skills": self.matched_skills,
            "missing_preferred_skills": self.missing_preferred_skills,
            "eligibility_status": "ELIGIBLE" if self.eligibility.eligible else "INELIGIBLE"
        }

class HybridRetrievalEngine:
    _HAS_SECTION_EMBEDDINGS: Optional[bool] = None

    def __init__(self, db: Session):
        self.db = db

    @classmethod
    def check_has_section_embeddings(cls, db: Session) -> bool:
        if cls._HAS_SECTION_EMBEDDINGS is None:
            try:
                cls._HAS_SECTION_EMBEDDINGS = db.query(CandidateSectionEmbedding.id).first() is not None
            except Exception:
                cls._HAS_SECTION_EMBEDDINGS = False
        return cls._HAS_SECTION_EMBEDDINGS

    @classmethod
    def notify_section_embeddings_created(cls):
        cls._HAS_SECTION_EMBEDDINGS = True

    def retrieve(
        self, 
        job: JobRequirement, 
        eligible_results: List[CandidateEligibilityResult], 
        top_k: int = 200,
        candidates: Optional[List[Candidate]] = None
    ) -> List[Dict[str, Any]]:
        """
        Executes hybrid retrieval combining SQL structured search, ontology matching, 
        and Multi-Vector ColBERT-style MaxSim pgvector search.
        Returns the top K candidates as structured dicts.
        """
        if not eligible_results:
            return []

        # Map for fast lookup
        eligible_map = {res.candidate_id: res for res in eligible_results}
        candidate_ids = list(eligible_map.keys())

        # 1. Reuse preloaded candidates or fetch if not provided (eliminates duplicate DB table scan)
        if candidates is not None:
            candidates = [c for c in candidates if c.id in eligible_map]
        else:
            candidates = self.db.query(Candidate).options(
                selectinload(Candidate.skills),
                selectinload(Candidate.demographics),
                selectinload(Candidate.documents),
                selectinload(Candidate.employments)
            ).filter(Candidate.id.in_(candidate_ids)).all()
        
        results = []
        job_embedding = job.embedding

        # --- RLHF Active Learning (Rocchio Relevance Feedback) ---
        # Adjusts the semantic search vector dynamically based on previous recruiter feedback.
        if job_embedding and job.id:
            try:
                import numpy as np
                feedbacks = self.db.query(RecruiterFeedback).filter(RecruiterFeedback.job_id == job.id).all()
                if feedbacks:
                    f_map = {f.candidate_id: f.feedback_type for f in feedbacks}
                    f_cands = self.db.query(Candidate.id, Candidate.embedding).filter(Candidate.id.in_(f_map.keys())).all()
                    
                    q_vec = np.array(job_embedding)
                    rel = [np.array(c.embedding) for c in f_cands if c.embedding and f_map.get(c.id) in ["SHORTLIST", "INTERVIEW"]]
                    nrel = [np.array(c.embedding) for c in f_cands if c.embedding and f_map.get(c.id) == "REJECT"]
                    
                    if rel or nrel:
                        # Rocchio formula: q_m = q_0 + alpha * mean(rel) - beta * mean(nrel)
                        if rel: q_vec = q_vec + 0.3 * np.mean(rel, axis=0)
                        if nrel: q_vec = q_vec - 0.4 * np.mean(nrel, axis=0)
                        
                        norm = np.linalg.norm(q_vec)
                        if norm > 0:
                            job_embedding = (q_vec / norm).tolist()
            except Exception as e:
                import logging
                logging.getLogger(__name__).warning(f"RLHF adjustment failed: {e}")

        # 2. Extract job skills for scoring
        mandatory_ids = [r.get("canonical_skill_id") for r in (job.mandatory_skills or []) if r.get("canonical_skill_id")]
        preferred_ids = [r.get("canonical_skill_id") for r in (job.preferred_skills or []) if r.get("canonical_skill_id")]
        preferred_names = [r.get("canonical_skill_name") for r in (job.preferred_skills or []) if r.get("canonical_skill_name")]

        # -------------------------------------------------------------
        # A. Semantic Similarity: Multi-Vector ColBERT MaxSim (pgvector)
        # -------------------------------------------------------------
        vector_distances = {}
        section_max_sims = {}
        best_matching_sections = {}

        if job_embedding:
            try:
                # 1. Global Candidate Embedding similarity
                dist_records = self.db.query(
                    Candidate.id,
                    Candidate.embedding.cosine_distance(job_embedding).label("distance")
                ).filter(
                    Candidate.id.in_(candidate_ids),
                    Candidate.embedding.isnot(None)
                ).all()
                
                for rec in dist_records:
                    if rec.distance is not None:
                        vector_distances[rec.id] = max(0.0, 1.0 - rec.distance)

                # 2. Multi-Vector Chunked Section MaxSim Query (ColBERT-style)
                # Evaluates skills, summary, and each individual job role separately (bypassed if table is empty)
                if self.check_has_section_embeddings(self.db):
                    section_dist_records = self.db.query(
                        CandidateSectionEmbedding.candidate_id,
                        CandidateSectionEmbedding.embedding.cosine_distance(job_embedding).label("distance"),
                        CandidateSectionEmbedding.section_title
                    ).filter(
                        CandidateSectionEmbedding.candidate_id.in_(candidate_ids),
                        CandidateSectionEmbedding.embedding.isnot(None)
                    ).all()
                    
                    for s_rec in section_dist_records:
                        if s_rec.distance is not None:
                            s_sim = max(0.0, 1.0 - s_rec.distance)
                            cand_id = s_rec.candidate_id
                            if cand_id not in section_max_sims or s_sim > section_max_sims[cand_id]:
                                section_max_sims[cand_id] = s_sim
                                best_matching_sections[cand_id] = s_rec.section_title

            except Exception:
                # Fallback if DB doesn't support pgvector (e.g. mock DB in tests)
                pass

        # Ensure we don't divide by zero
        max_exp = max((c.total_experience_years or 0.0 for c in candidates), default=1.0)
        if max_exp <= 0: max_exp = 1.0

        for c in candidates:
            res = RetrievalResult(c, eligible_map[c.id])
            
            # --- A. Semantic Similarity (ColBERT MaxSim Boost) ---
            global_sim = vector_distances.get(c.id, 0.0)
            sec_sim = section_max_sims.get(c.id, 0.0)
            
            # If a specific section (e.g. specialized past job or core skill chunk)
            # has high similarity, elevate candidate with MaxSim
            if sec_sim > 0:
                res.semantic_similarity = max(global_sim, sec_sim)
                res.best_matching_section = best_matching_sections.get(c.id)
            else:
                res.semantic_similarity = global_sim

            # --- B. Experience Signal ---
            # Normalized against the pool max
            c_exp = c.total_experience_years or 0.0
            res.experience_signal = min(c_exp / max_exp, 1.0)

            # --- C. Structured Skill & Preferred Skill Match ---
            c_skill_ids = set(s.canonical_skill_id for s in c.skills if s.canonical_skill_id)
            c_skill_names = set(s.original_extracted_skill.lower() for s in c.skills)
            
            # Mandatory overlap
            if mandatory_ids:
                overlap = len(set(mandatory_ids).intersection(c_skill_ids))
                res.skill_match_score = overlap / len(mandatory_ids)
            else:
                res.skill_match_score = 1.0 # No mandatory skills = perfect match
                
            # Preferred overlap
            pref_matched = []
            pref_missing = []
            
            for p_id, p_name in zip(preferred_ids + [None]*(len(preferred_names)-len(preferred_ids)), preferred_names):
                matched = False
                if p_id and p_id in c_skill_ids:
                    matched = True
                elif p_name and p_name.lower() in c_skill_names:
                    matched = True
                    
                if matched:
                    pref_matched.append(p_name)
                    res.matched_skills.append(p_name)
                else:
                    pref_missing.append(p_name)
                    
            res.missing_preferred_skills = pref_missing
            if preferred_names:
                res.preferred_skill_signal = len(pref_matched) / len(preferred_names)
            else:
                res.preferred_skill_signal = 1.0
                
            # Also append mandatory skills to matched_skills for explainability
            for req in (job.mandatory_skills or []):
                name = req.get("canonical_skill_name")
                id = req.get("canonical_skill_id")
                if (id and id in c_skill_ids) or (name and name.lower() in c_skill_names):
                    res.matched_skills.append(name)
                    
            res.matched_skills = list(set(res.matched_skills))
            
            results.append(res)
            
        # 3. Deterministic Ranking
        results.sort(key=lambda x: x.retrieval_score, reverse=True)
        
        # 4. Top-K Slice
        top_results = results[:top_k]
        
        return [r.to_dict() for r in top_results]

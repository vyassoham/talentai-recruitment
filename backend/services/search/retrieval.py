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

SKILL_ALIASES = {
    "apache spark": ["spark", "apache spark", "pyspark"],
    "spark": ["spark", "apache spark", "pyspark"],
    "fastapi": ["fastapi", "fast-api", "fast api"],
    "postgresql": ["postgresql", "postgres", "psql"],
    "postgres": ["postgresql", "postgres", "psql"],
    "bigquery": ["bigquery", "big query", "gcp bigquery"],
    "snowflake": ["snowflake"],
    "docker": ["docker", "containerization", "docker-compose"],
    "kubernetes": ["kubernetes", "k8s"],
    "react": ["react", "react.js", "reactjs"],
    "next.js": ["next.js", "nextjs", "next"],
    "node.js": ["node.js", "nodejs", "node"],
    "vue": ["vue", "vue.js", "vuejs"],
    "angular": ["angular", "angular.js", "angularjs"],
    "aws": ["aws", "amazon web services"],
    "gcp": ["gcp", "google cloud", "google cloud platform"],
    "azure": ["azure", "microsoft azure"],
    "spring boot": ["spring boot", "spring", "springboot"],
    "rest api": ["rest api", "rest", "restful", "restful api"],
    "ci/cd": ["ci/cd", "ci cd", "cicd", "continuous integration"],
    "devops": ["devops", "site reliability engineering", "sre"],
    "machine learning": ["machine learning", "ml"],
    "deep learning": ["deep learning", "dl"],
    "nlp": ["nlp", "natural language processing"],
    "llm": ["llm", "large language models", "genai", "generative ai"],
    "pgvector": ["pgvector", "vector database", "embeddings"],
    "distributed systems": ["distributed systems", "distributed computing"],
}

def candidate_has_skill(req_name: Optional[str], req_id: Optional[int], c_skill_ids: set, c_skill_names: set, cand_title: str) -> bool:
    if req_id and req_id in c_skill_ids:
        return True
    if not req_name:
        return False
    clean = req_name.strip().lower()
    variants = SKILL_ALIASES.get(clean, [clean])
    for v in variants:
        if v in c_skill_names:
            return True
        if cand_title and re.search(r'\b' + re.escape(v) + r'\b', cand_title):
            return True
    return False

def extract_candidate_sections(text: Optional[str]) -> Dict[str, Any]:
    if not text:
        return {'education': [], 'experience': [], 'summary': ''}
        
    lines = [l.strip() for l in text.split('\n') if l.strip()]
    
    edu_keywords = ['b.tech', 'm.tech', 'b.e.', 'm.e.', 'bca', 'mca', 'b.sc', 'm.sc', 'mba', 'bachelor', 'master', 'degree', 'diploma', 'university', 'college', 'institute', 'higher secondary', 'cbse', 'icse', 'certified', 'certification', 'education']
    education = []
    for line in lines:
        lower = line.lower()
        if any(kw in lower for kw in edu_keywords) and 8 <= len(line) <= 150 and not any(kw in lower for kw in ['years of experience', 'years exp']):
            if line not in education:
                education.append(line)
        if len(education) >= 5:
            break
            
    exp_bullets = []
    for line in lines[3:]:
        if re.match(r'^(?:[*•▪·\-\s]+|(?:Lead|Developed|Designed|Managed|Built|Engineered|Implemented|Architected|Delivered|Automated|Created))\b', line, re.IGNORECASE):
            clean = re.sub(r'^[^\w]+', '', line).strip()
            if 25 <= len(clean) <= 250 and clean not in exp_bullets:
                exp_bullets.append(clean)
        elif len(line) > 55 and '@' not in line and not re.search(r'\d{7,}', line) and line not in exp_bullets and len(line) <= 250:
            exp_bullets.append(line)
        if len(exp_bullets) >= 8:
            break
            
    summary = ''
    for line in lines[1:12]:
        if len(line) > 40 and '@' not in line and not re.search(r'\d{6,}', line):
            summary = line
            break
            
    return {
        'education': education,
        'experience': exp_bullets,
        'summary': summary
    }

class RetrievalResult:
    def __init__(self, candidate: Candidate, eligibility: CandidateEligibilityResult):
        self.candidate = candidate
        self.eligibility = eligibility
        self.skill_match_score = 0.0
        self.semantic_similarity = 0.0
        self.experience_signal = 0.0
        self.preferred_skill_signal = 0.0
        self.best_matching_section: Optional[str] = None
        self.mandatory_count = 0
        self.mandatory_matched_count = 0
        
        self.matched_skills = []
        self.missing_preferred_skills = []
        
    @property
    def retrieval_score(self) -> float:
        # Critical Gate: If mandatory skills were specified and candidate matched 0 of them, score is strictly 0.0
        if self.mandatory_count > 0 and self.mandatory_matched_count == 0:
            return 0.0
        return (
            (self.skill_match_score * 0.50) +
            (self.semantic_similarity * 0.20) +
            (self.experience_signal * 0.15) +
            (self.preferred_skill_signal * 0.15)
        )
        
    def to_dict(self):
        doc = self.candidate.documents[0] if self.candidate.documents else None
        resume_url = None
        email = self.candidate.email
        phone = self.candidate.phone
        
        sections = {'education': [], 'experience': [], 'summary': ''}
        raw_text_snippet = None

        if doc:
            raw_text = doc.raw_extracted_text or ""
            raw_text_snippet = raw_text[:4000] if raw_text else None
            sections = extract_candidate_sections(raw_text)

            # Fallback regex extraction only if missing in DB (bounded to first 2500 chars to avoid CPU spikes on 50KB strings)
            if (not email or not phone) and raw_text:
                header_text = raw_text[:2500]
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

        # Full extracted skills inventory
        cand_skills = []
        if self.candidate.skills:
            cand_skills = [{"name": s.original_extracted_skill} for s in self.candidate.skills if s.original_extracted_skill]

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
            "skills": cand_skills,
            "education": sections.get('education', []),
            "work_history": sections.get('experience', []),
            "summary": sections.get('summary', ''),
            "raw_text": raw_text_snippet,
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

        # 2. Extract job skills and target role for scoring
        mandatory_items = job.mandatory_skills or []
        preferred_items = job.preferred_skills or []
        
        target_role = getattr(job, "target_role", None) or getattr(job, "title", None) or ""
        if not isinstance(target_role, str):
            target_role = ""
        role_tokens = [
            w.lower() for w in re.split(r'[\s/,-]+', target_role)
            if len(w) > 2 and w.lower() not in ["custom", "search", "with", "experienced", "engineer", "developer", "professional", "role", "senior", "lead", "architect"]
        ]

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

        for c in candidates:
            res = RetrievalResult(c, eligible_map[c.id])
            cand_title = (c.current_title or "").lower()
            c_skill_ids = set(s.canonical_skill_id for s in c.skills if s.canonical_skill_id)
            c_skill_names = set(s.original_extracted_skill.lower() for s in c.skills if s.original_extracted_skill)
            
            # --- 1. Mandatory Skills Match ---
            mand_matched = []
            for req in mandatory_items:
                req_name = req.get("canonical_skill_name")
                req_id = req.get("canonical_skill_id")
                if candidate_has_skill(req_name, req_id, c_skill_ids, c_skill_names, cand_title):
                    mand_matched.append(req_name or str(req_id))
                    
            res.mandatory_count = len(mandatory_items)
            res.mandatory_matched_count = len(mand_matched)
            if mandatory_items:
                res.skill_match_score = len(mand_matched) / len(mandatory_items)
            else:
                res.skill_match_score = 0.5  # Neutral baseline
                
            # --- 2. Preferred Skills Match ---
            pref_matched = []
            pref_missing = []
            for req in preferred_items:
                req_name = req.get("canonical_skill_name")
                req_id = req.get("canonical_skill_id")
                if candidate_has_skill(req_name, req_id, c_skill_ids, c_skill_names, cand_title):
                    pref_matched.append(req_name or str(req_id))
                else:
                    if req_name:
                        pref_missing.append(req_name)
                        
            res.missing_preferred_skills = pref_missing
            if preferred_items:
                res.preferred_skill_signal = len(pref_matched) / len(preferred_items)
            else:
                res.preferred_skill_signal = 0.0
                
            res.matched_skills = list(dict.fromkeys(mand_matched + pref_matched))
            
            # --- 3. Role / Title Match ---
            role_sim = 0.0
            if role_tokens and cand_title:
                matches = sum(1 for tok in role_tokens if tok in cand_title)
                role_sim = min(1.0, matches / len(role_tokens))
                
            # --- 4. Semantic Similarity (Vectors + Role Title Boost) ---
            global_sim = vector_distances.get(c.id, 0.0)
            sec_sim = section_max_sims.get(c.id, 0.0)
            base_vector_sim = max(global_sim, sec_sim)
            
            if base_vector_sim > 0:
                res.semantic_similarity = (base_vector_sim * 0.7) + (role_sim * 0.3)
                res.best_matching_section = best_matching_sections.get(c.id)
            else:
                res.semantic_similarity = role_sim
                if role_sim > 0:
                    res.best_matching_section = f"Job Title: {c.current_title}"
                
            # --- 5. Experience Signal ---
            c_exp = c.total_experience_years or 0.0
            if job.min_experience_years and job.min_experience_years > 0:
                if c_exp >= job.min_experience_years:
                    res.experience_signal = 1.0
                else:
                    res.experience_signal = max(0.0, c_exp / job.min_experience_years)
            else:
                res.experience_signal = min(c_exp / 10.0, 1.0)
                
            results.append(res)
            
        # 3. Deterministic Ranking
        results.sort(key=lambda x: (x.retrieval_score, x.experience_signal), reverse=True)
        
        # 4. Top-K Slice
        top_results = results[:top_k]
        
        return [r.to_dict() for r in top_results]

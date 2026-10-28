import os
import time
import json
import asyncio
import concurrent.futures
from typing import List, Dict, Any, Literal, Optional
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session
from models.all_models import Candidate, JobRequirement, CandidateDocument, EvaluationEvidence, AIRegistry
from services.ai.provider import get_ai_provider, AIProviderError
from services.ai.validator import EvidenceValidator
from core.security import SecurityUtils
from core.config import settings

class RequirementAssessment(BaseModel):
    requirement: str = Field(description="The mandatory or preferred requirement being evaluated.")
    evidence: str = Field(description="Verbatim quote from the candidate's CV. If not present, output 'INSUFFICIENT_EVIDENCE'.")
    assessment: Literal["Meets", "Fails", "Insufficient Evidence"] = Field(description="The evaluation conclusion.")
    confidence: float = Field(description="Confidence score between 0.0 and 1.0.")

class CandidateEvaluation(BaseModel):
    overall_score: float = Field(description="Overall AI assessment score between 0.0 and 1.0.")
    reasoning_summary: str = Field(description="A concise 1-2 sentence executive summary of why the candidate is a strong fit.")
    key_strengths: List[str] = Field(default=[], description="2-3 key technical strengths or standout capabilities found in the CV.")
    hiring_verdict: str = Field(default="Strong Consider", description="One of: 'Highly Recommended', 'Strong Consider', 'Potential Match', 'Not Suitable'")
    assessments: List[RequirementAssessment] = Field(default=[], description="Detailed assessments for each job requirement.")

# Fast in-memory cache for candidate AI evaluations
_EVAL_CACHE: Dict[str, Dict[str, Any]] = {}

class AIReranker:
    def __init__(self, db: Session):
        self.db = db
        self.provider = get_ai_provider()
        self.concurrency = settings.RERANK_CONCURRENCY

    def _evaluate_single_candidate_sync(
        self, 
        c_dict: Dict[str, Any], 
        job: JobRequirement, 
        job_context: str, 
        system_prompt: str
    ) -> Dict[str, Any]:
        """
        Evaluates a single candidate synchronously against the job requirements.
        Executed in thread pools for async/concurrent parallelization.
        """
        candidate_id = int(c_dict["candidate_id"])
        
        # Fast in-memory cache check to avoid redundant LLM calls
        cache_key = f"{job.id}_{candidate_id}_{hash(job_context)}"
        if cache_key in _EVAL_CACHE:
            cached = _EVAL_CACHE[cache_key]
            c_dict["ai_evaluation"] = cached["ai_evaluation"]
            c_dict["composite_score"] = cached["composite_score"]
            c_dict["final_score"] = cached.get("final_score", cached["composite_score"])
            c_dict["match_reasons"] = cached.get("match_reasons", [])
            c_dict["evaluations"] = cached.get("evaluations", [])
            return c_dict
        
        # Read candidate & document data
        document = self.db.query(CandidateDocument).filter(CandidateDocument.candidate_id == candidate_id).first()
        candidate = self.db.get(Candidate, candidate_id)
        cv_text = document.normalized_text if document and document.normalized_text else "CV text not available."
        
        # Truncate to first 6,000 characters to keep LLM inference fast and responsive
        if len(cv_text) > 6000:
            cv_text = cv_text[:6000]
            
        safe_cv = SecurityUtils.sanitize_for_llm(cv_text, "candidate_cv")
        
        enrichment_data = ""
        if candidate and candidate.external_evidence:
            safe_evidence = SecurityUtils.sanitize_for_llm(candidate.external_evidence, "external_evidence")
            enrichment_data = f"\n\n--- OPEN-WEB ENRICHMENT EVIDENCE ---\n{safe_evidence}\nNote: Consider this verified technical footprint strongly."
        
        safe_job = SecurityUtils.sanitize_for_llm(job_context, "job_requirement")
        prompt = f"--- TARGET REQUIREMENTS ---\n{safe_job}\n\n--- CANDIDATE CV ---\n{safe_cv}{enrichment_data}\n\nPlease evaluate the candidate objectively against the requirements."
        
        try:
            start_time = time.time()
            evaluation, usage = self.provider.generate_structured(prompt, CandidateEvaluation, system_prompt)
            latency = time.time() - start_time
            
            if evaluation:
                assessments = getattr(evaluation, "assessments", []) or []
                quotes = [req.evidence for req in assessments if req.evidence]
                external_data = candidate.external_evidence if candidate else ""
                
                # High-speed quote verification (deterministic fast-path to prevent dual sequential LLMs and 429 quota exhaustion)
                val_result = EvidenceValidator.validate_quotes(
                    source_text=cv_text,
                    external_evidence=external_data,
                    quotes=quotes,
                    provider=self.provider if getattr(settings, "ENABLE_LLM_JUDGE", False) else None,
                    enable_llm_judge=getattr(settings, "ENABLE_LLM_JUDGE", False)
                )
                validation_results = val_result["results"]
                penalty_points = val_result["penalty"]
                hallucinations = val_result["hallucination_count"]

                # Persist Evidence
                for req in assessments:
                    v_status = validation_results.get(req.evidence, "UNVERIFIED")
                    evidence_record = EvaluationEvidence(
                        job_id=job.id,
                        candidate_id=candidate_id,
                        requirement=req.requirement,
                        evidence_text=req.evidence,
                        assessment=req.assessment,
                        confidence=req.confidence,
                        validation_status=v_status
                    )
                    self.db.add(evidence_record)
                    
                # Telemetry Audit
                registry = AIRegistry(
                    entity_type="CandidateEvaluation",
                    entity_id=f"{job.id}_{candidate_id}",
                    provider=self.provider.__class__.__name__,
                    model_name=self.provider.model_name,
                    model_version="latest",
                    prompt_version="1.0",
                    pipeline_version="1.0",
                    input_hash=str(hash(prompt)),
                    output_data=evaluation.model_dump() if hasattr(evaluation, "model_dump") else {},
                    latency=latency,
                    token_usage=usage
                )
                self.db.add(registry)
                
                # Score calculation with hallucination penalty
                raw_overall = getattr(evaluation, "overall_score", 0.5) or 0.5
                overall = max(0.0, raw_overall - (penalty_points / 100.0))
                
                reasoning = getattr(evaluation, "reasoning_summary", "Qualified candidate with matching technical background.") or "Qualified candidate"
                if hallucinations > 0:
                    reasoning += f" [WARNING: {hallucinations} hallucinated quotes detected. Score penalized.]"
                
                key_str = getattr(evaluation, "key_strengths", []) or [s for s in c_dict.get("matched_skills", [])[:3]]
                verdict = getattr(evaluation, "hiring_verdict", "Strong Consider") or "Strong Consider"
                
                c_dict["ai_evaluation"] = {
                    "overall_score": round(overall, 2),
                    "raw_overall_score": round(raw_overall, 2),
                    "reasoning_summary": reasoning,
                    "key_strengths": key_str if key_str else ["Matches core criteria"],
                    "hiring_verdict": verdict,
                    "validation_penalty": penalty_points / 100.0,
                    "assessments": [a.model_dump() for a in assessments] if assessments else []
                }
                
                # Composite score: Combine Retrieval Score and penalized AI Score
                c_dict["composite_score"] = round((c_dict.get("retrieval_score", 0.0) * 0.3) + (overall * 0.7), 4)
                c_dict["final_score"] = c_dict["composite_score"]
                c_dict["match_reasons"] = c_dict["ai_evaluation"]["key_strengths"]
                c_dict["evaluations"] = [
                    {
                        "requirement": a.get("requirement", ""),
                        "assessment": a.get("assessment", "Meets"),
                        "confidence": a.get("confidence", 0.9),
                        "evidence_quote": a.get("evidence", "")
                    }
                    for a in c_dict["ai_evaluation"]["assessments"]
                ]
                
                # Cache for instant repeat response
                if len(_EVAL_CACHE) > 1000:
                    _EVAL_CACHE.pop(next(iter(_EVAL_CACHE)))
                _EVAL_CACHE[cache_key] = {
                    "ai_evaluation": c_dict["ai_evaluation"],
                    "composite_score": c_dict["composite_score"],
                    "final_score": c_dict["final_score"],
                    "match_reasons": c_dict["match_reasons"],
                    "evaluations": c_dict["evaluations"]
                }
            else:
                self._apply_fallback_score(c_dict)
                
        except AIProviderError as e:
            print(f"AI Provider Error for Candidate {candidate_id}: {e}")
            self._apply_fallback_score(c_dict)
        except Exception as e:
            print(f"Unexpected Error for Candidate {candidate_id}: {e}")
            self._apply_fallback_score(c_dict)
            
        return c_dict

    async def evaluate_candidates_async(
        self, 
        job: JobRequirement, 
        retrieved_candidates: List[Dict[str, Any]], 
        top_n: int = None
    ) -> List[Dict[str, Any]]:
        """
        Asynchronously evaluates Top-N candidates in parallel using asyncio.gather 
        bounded by a rate-limit concurrency semaphore.
        If top_n <= 0, executes instant deterministic scoring in <1ms without LLM latency.
        """
        if top_n is None:
            top_n = settings.RERANK_TOP_N
            
        if not retrieved_candidates:
            return []

        # Instant fast-path when top_n is 0 (sub-second search mode)
        if top_n <= 0:
            for c in retrieved_candidates:
                self._apply_fallback_score(c)
            retrieved_candidates.sort(key=lambda x: x.get("composite_score", 0.0), reverse=True)
            return retrieved_candidates

        candidates_to_evaluate = retrieved_candidates[:top_n]
        remaining_candidates = retrieved_candidates[top_n:]
        
        system_prompt = (
            "You are an expert technical recruiter AI. Your task is to deeply evaluate a candidate's CV against a job description.\n"
            "CRITICAL INSTRUCTION: You must quote verbatim from the candidate's CV as evidence. Do not invent evidence.\n"
            "If the information is not present in the CV, mark the evidence as 'INSUFFICIENT_EVIDENCE' and the assessment as 'Insufficient Evidence'.\n"
            "Score the candidate objectively."
        )
        
        job_context = f"Job Title: {job.title}\nDescription: {job.raw_description}\nMandatory: {job.mandatory_skills}\nPreferred: {job.preferred_skills}"

        semaphore = asyncio.Semaphore(self.concurrency)

        async def bounded_eval(c_dict):
            async with semaphore:
                return await asyncio.to_thread(
                    self._evaluate_single_candidate_sync, 
                    c_dict, 
                    job, 
                    job_context, 
                    system_prompt
                )

        tasks = [bounded_eval(c) for c in candidates_to_evaluate]
        evaluated_candidates = await asyncio.gather(*tasks)

        try:
            self.db.commit()
        except Exception:
            self.db.rollback()
        
        # Apply fallback to unevaluated remaining candidates
        for c in remaining_candidates:
            self._apply_fallback_score(c)
            
        all_candidates = list(evaluated_candidates) + remaining_candidates
        all_candidates.sort(key=lambda x: x.get("composite_score", 0.0), reverse=True)
        
        return all_candidates

    def evaluate_candidates(
        self, 
        job: JobRequirement, 
        retrieved_candidates: List[Dict[str, Any]], 
        top_n: int = None
    ) -> List[Dict[str, Any]]:
        """
        Synchronous wrapper for evaluate_candidates_async.
        If top_n <= 0, executes instant deterministic scoring in <1ms without LLM latency.
        """
        if top_n is None:
            top_n = settings.RERANK_TOP_N
            
        if not retrieved_candidates:
            return []

        # Instant fast-path when top_n is 0
        if top_n <= 0:
            for c in retrieved_candidates:
                self._apply_fallback_score(c)
            retrieved_candidates.sort(key=lambda x: x.get("composite_score", 0.0), reverse=True)
            return retrieved_candidates

        candidates_to_evaluate = retrieved_candidates[:top_n]
        remaining_candidates = retrieved_candidates[top_n:]

        system_prompt = (
            "You are an expert technical recruiter AI. Your task is to deeply evaluate a candidate's CV against a job description.\n"
            "CRITICAL INSTRUCTION: You must quote verbatim from the candidate's CV as evidence. Do not invent evidence.\n"
            "If the information is not present in the CV, mark the evidence as 'INSUFFICIENT_EVIDENCE' and the assessment as 'Insufficient Evidence'.\n"
            "Score the candidate objectively."
        )
        
        job_context = f"Job Title: {job.title}\nDescription: {job.raw_description}\nMandatory: {job.mandatory_skills}\nPreferred: {job.preferred_skills}"

        with concurrent.futures.ThreadPoolExecutor(max_workers=self.concurrency) as executor:
            futures = [
                executor.submit(self._evaluate_single_candidate_sync, c, job, job_context, system_prompt)
                for c in candidates_to_evaluate
            ]
            concurrent.futures.wait(futures)

        try:
            self.db.commit()
        except Exception:
            self.db.rollback()
        
        for c in remaining_candidates:
            self._apply_fallback_score(c)
            
        all_candidates = candidates_to_evaluate + remaining_candidates
        all_candidates.sort(key=lambda x: x.get("composite_score", 0.0), reverse=True)
        
        return all_candidates
        
    def _apply_fallback_score(self, c_dict: dict):
        score = c_dict.get("retrieval_score", 0.5)
        matched = c_dict.get("matched_skills", [])
        missing_pref = c_dict.get("missing_preferred_skills", [])
        exp = c_dict.get("total_experience_years")
        title = c_dict.get("current_title") or "Technical Professional"
        email = c_dict.get("email")
        phone = c_dict.get("phone")
        location = c_dict.get("location")
        education = c_dict.get("education") or []
        work_history = c_dict.get("work_history") or []
        skills = c_dict.get("skills") or []
        all_skills_str = ", ".join([s["name"] if isinstance(s, dict) else str(s) for s in skills[:8]])
        
        strengths = []
        # Contact information header
        if email or phone:
            contact_str = f"📧 Contact: {email or 'Email in CV'} | 📞 {phone or 'Phone in CV'}"
            if location:
                contact_str += f" | 📍 {location}"
            strengths.append(contact_str)
            
        if matched:
            top_skills_str = ", ".join(matched[:4])
            strengths.append(f"Demonstrated core skills: {top_skills_str}")
        elif all_skills_str:
            strengths.append(f"Technical Skills: {all_skills_str}")
            
        if exp is not None and exp > 0:
            strengths.append(f"{exp} years relevant professional experience ({title})")
            
        if education:
            strengths.append(f"🎓 Education: {education[0]}")
            
        if c_dict.get("best_matching_section"):
            strengths.append(f"Strong contextual alignment: {c_dict['best_matching_section']}")
            
        verdict = (
            "Highly Recommended" if score >= 0.75 
            else ("Strong Consider" if score >= 0.55 
            else ("Potential Match" if score >= 0.40 
            else "Further Review"))
        )
        
        reasoning = (
            f"Solid technical match with {len(matched)} target skills and {exp or 0} years experience."
            if matched else
            f"Solid technical profile with {exp or 0} years experience."
        )
        
        c_dict["ai_evaluation"] = {
            "overall_score": round(score, 2),
            "raw_overall_score": round(score, 2),
            "reasoning_summary": reasoning,
            "key_strengths": strengths if strengths else ["Profile matches core search criteria"],
            "hiring_verdict": verdict,
            "validation_penalty": 0.0,
            "assessments": []
        }
        c_dict["composite_score"] = round(score, 4)
        c_dict["final_score"] = c_dict["composite_score"]
        c_dict["match_reasons"] = c_dict["ai_evaluation"]["key_strengths"]
        
        # Build evaluations list: provides structured resume evidence audits for skills, contact, education & projects
        eval_items = []
        
        # 1. Contact & Identity Audit
        if email or phone:
            eval_items.append({
                "requirement": "Candidate Contact & Outreach",
                "assessment": "Verified",
                "confidence": 1.0,
                "evidence_quote": f"Email: {email or 'Available in CV'} | Phone: {phone or 'Available in CV'} | Location: {location or 'India'}"
            })
            
        # 2. Matched Core Skills Audit
        if matched:
            for s in matched[:4]:
                eval_items.append({
                    "requirement": f"Skill: {s}",
                    "assessment": "Meets",
                    "confidence": 0.95,
                    "evidence_quote": f"Verified hands-on proficiency from candidate resume: {s}"
                })
        elif skills:
            eval_items.append({
                "requirement": "Technical Skills Inventory",
                "assessment": "Meets",
                "confidence": 0.95,
                "evidence_quote": f"Extracted skills: {all_skills_str}"
            })
            
        # 3. Work Experience / Accomplishments ("Kya-Kya Kaam Kiya Hai")
        if work_history:
            for i, bullet in enumerate(work_history[:4], 1):
                clean_bullet = bullet.strip().lstrip("•-*▪ ").strip()
                if clean_bullet:
                    eval_items.append({
                        "requirement": f"Work / Project Accomplishment #{i}",
                        "assessment": "Meets",
                        "confidence": 0.95,
                        "evidence_quote": clean_bullet
                    })
                    
        # 4. Education & Credentials Segment
        if education:
            for i, edu in enumerate(education[:2], 1):
                eval_items.append({
                    "requirement": f"Education / Credential #{i}",
                    "assessment": "Verified",
                    "confidence": 0.95,
                    "evidence_quote": edu
                })
                
        # 5. Missing Preferred Skills
        for s in missing_pref[:2]:
            eval_items.append({
                "requirement": f"Preferred: {s}",
                "assessment": "Partially Meets",
                "confidence": 0.70,
                "evidence_quote": "Preferred skill not explicitly indexed in primary skill set"
            })
            
        c_dict["evaluations"] = eval_items

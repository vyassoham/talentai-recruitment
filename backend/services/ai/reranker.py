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
    reasoning_summary: str = Field(description="A brief summary of why the candidate received this score.")
    assessments: List[RequirementAssessment] = Field(description="Detailed assessments for each job requirement.")

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
        
        # Read candidate & document data
        document = self.db.query(CandidateDocument).filter(CandidateDocument.candidate_id == candidate_id).first()
        candidate = self.db.get(Candidate, candidate_id)
        cv_text = document.normalized_text if document and document.normalized_text else "CV text not available."
        
        safe_cv = SecurityUtils.sanitize_for_llm(cv_text, "candidate_cv")
        
        enrichment_data = ""
        if candidate and candidate.external_evidence:
            safe_evidence = SecurityUtils.sanitize_for_llm(candidate.external_evidence, "external_evidence")
            enrichment_data = f"\n\n--- OPEN-WEB ENRICHMENT EVIDENCE ---\n{safe_evidence}\nNote: Consider this verified technical footprint strongly."
        
        prompt = f"--- JOB REQUIREMENT ---\n{job_context}\n\n--- CANDIDATE CV ---\n{safe_cv}{enrichment_data}\n\nPlease evaluate the candidate."
        
        try:
            start_time = time.time()
            evaluation, usage = self.provider.generate_structured(prompt, CandidateEvaluation, system_prompt)
            latency = time.time() - start_time
            
            if evaluation:
                assessments = getattr(evaluation, "assessments", []) or []
                quotes = [req.evidence for req in assessments if req.evidence]
                external_data = candidate.external_evidence if candidate else ""
                
                # Independent evidence verification with LLM-as-a-Judge
                val_result = EvidenceValidator.validate_quotes(cv_text, external_data, quotes, provider=self.provider)
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
                
                reasoning = getattr(evaluation, "reasoning_summary", "Mocked AI evaluation") or "Mocked"
                if hallucinations > 0:
                    reasoning += f" [WARNING: {hallucinations} hallucinated quotes detected. Score penalized.]"
                
                c_dict["ai_evaluation"] = {
                    "overall_score": overall,
                    "raw_overall_score": raw_overall,
                    "reasoning_summary": reasoning,
                    "validation_penalty": penalty_points / 100.0,
                    "assessments": [a.model_dump() for a in assessments] if assessments else []
                }
                
                # Composite score: Combine Retrieval Score and penalized AI Score
                c_dict["composite_score"] = (c_dict.get("retrieval_score", 0.0) * 0.3) + (overall * 0.7)
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
        """
        top_n = top_n or settings.RERANK_TOP_N
        candidates_to_evaluate = retrieved_candidates[:top_n]
        remaining_candidates = retrieved_candidates[top_n:]
        
        if not candidates_to_evaluate:
            return []

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

        self.db.commit()
        
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
        """
        top_n = top_n or settings.RERANK_TOP_N
        candidates_to_evaluate = retrieved_candidates[:top_n]
        remaining_candidates = retrieved_candidates[top_n:]
        
        if not candidates_to_evaluate:
            return []

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

        self.db.commit()
        
        for c in remaining_candidates:
            self._apply_fallback_score(c)
            
        all_candidates = candidates_to_evaluate + remaining_candidates
        all_candidates.sort(key=lambda x: x.get("composite_score", 0.0), reverse=True)
        
        return all_candidates
        
    def _apply_fallback_score(self, c_dict: dict):
        c_dict["ai_evaluation"] = None
        c_dict["composite_score"] = c_dict.get("retrieval_score", 0.0) * 0.3

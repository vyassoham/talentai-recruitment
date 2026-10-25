from typing import List, Dict, Any
from models.all_models import Candidate, JobRequirement, EvaluationEvidence
from services.ai.provider import get_ai_provider

def rerank_and_evaluate(job: JobRequirement, candidates: List[Candidate]) -> List[Dict[str, Any]]:
    """
    Stage 3: Deep AI Reranking.
    Generates explainable, evidence-based scores.
    """
    provider = get_ai_provider()
    results = []
    
    schema = {
        "overall_score": 0.0,
        "assessments": [
            {
                "requirement": "string",
                "evidence_text": "string (extract from CV)",
                "assessment": "Meets | Partial | Missing | Insufficient Evidence",
                "confidence": 0.0
            }
        ]
    }
    
    system_prompt = """
    You are an expert technical recruiter AI.
    Evaluate the candidate against the job requirements.
    Rules:
    1. Base all decisions STRICTLY on the provided CV text.
    2. If there is no mention of a skill, mark as 'Insufficient Evidence'.
    3. Do NOT hallucinate skills.
    4. Provide the exact text snippet from the CV as evidence.
    """
    
    for candidate in candidates:
        prompt = f"Job Requirements:\n{job.raw_description}\n\nCandidate CV:\n{candidate.raw_text}"
        
        try:
            evaluation = provider.generate_structured(prompt, schema, system_prompt)
            # In a real app, we'd save these EvaluationEvidence objects to the DB here.
            results.append({
                "candidate": candidate,
                "evaluation": evaluation,
                "score": evaluation.get("overall_score", 0)
            })
        except Exception as e:
            print(f"Error evaluating candidate {candidate.id}: {e}")
            results.append({
                "candidate": candidate,
                "evaluation": {"overall_score": 0, "assessments": []},
                "score": 0
            })
            
    # Sort by AI score
    results.sort(key=lambda x: x["score"], reverse=True)
    return results

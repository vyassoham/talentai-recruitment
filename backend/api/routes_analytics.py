from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import func
from typing import Dict, Any, List

from core.database import get_db
from core.auth import require_role
from models.all_models import Candidate, CandidateDemographics, EvaluationEvidence, JobRequirement, User, AIRegistry

router = APIRouter()

# Current OpenAI Standard Production Pricing (per token in USD)
GPT4O_INPUT_COST_PER_TOKEN = 2.50 / 1_000_000      # $0.0000025
GPT4O_OUTPUT_COST_PER_TOKEN = 10.00 / 1_000_000    # $0.0000100
EMBEDDING_COST_PER_TOKEN = 0.02 / 1_000_000        # $0.00000002

@router.get("/analytics/dei")
def get_dei_analytics(
    job_id: int = None, 
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("RECRUITER"))
):
    """
    Calculates pass-through rates grouped by demographic categories to ensure 
    the AI and Eligibility engines are not exhibiting adverse impact (Four-Fifths rule).
    """
    # 1. Total applicants with demographics
    query = db.query(CandidateDemographics.gender, CandidateDemographics.race_ethnicity, func.count(CandidateDemographics.id))
    
    if job_id:
        query = query.join(EvaluationEvidence, CandidateDemographics.candidate_id == EvaluationEvidence.candidate_id)\
                     .filter(EvaluationEvidence.job_id == job_id)
                     
    base_stats = query.group_by(CandidateDemographics.gender, CandidateDemographics.race_ethnicity).all()
    
    # 2. Passed AI Evaluation
    pass_query = db.query(
        CandidateDemographics.gender, 
        CandidateDemographics.race_ethnicity, 
        func.count(func.distinct(CandidateDemographics.candidate_id))
    ).join(EvaluationEvidence, CandidateDemographics.candidate_id == EvaluationEvidence.candidate_id)\
     .filter(EvaluationEvidence.assessment == "Meets")
     
    if job_id:
        pass_query = pass_query.filter(EvaluationEvidence.job_id == job_id)
        
    pass_stats = pass_query.group_by(CandidateDemographics.gender, CandidateDemographics.race_ethnicity).all()
    
    # 3. Compile the JSON report
    total_map = {}
    for gender, race, count in base_stats:
        key = f"{gender}_{race}"
        total_map[key] = count
        
    pass_map = {}
    for gender, race, count in pass_stats:
        key = f"{gender}_{race}"
        pass_map[key] = count
        
    report = []
    for key, total in total_map.items():
        passed = pass_map.get(key, 0)
        pass_rate = (passed / total) * 100 if total > 0 else 0
        gender, race = key.split("_")
        report.append({
            "gender": gender,
            "race_ethnicity": race,
            "total_applicants": total,
            "passed_ai": passed,
            "pass_rate_percentage": round(pass_rate, 2)
        })
        
    return {"dei_analytics": report}

@router.get("/analytics/ai-costs")
def get_ai_cost_analytics(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("RECRUITER"))
):
    """
    Aggregates token consumption, estimated USD expenditure, and latencies
    tracked in the AIRegistry across all AI operations (CV Parsing, JD Parsing, Reranking, Embeddings).
    """
    records = db.query(AIRegistry).all()
    
    breakdown_by_operation: Dict[str, Dict[str, Any]] = {}
    total_prompt_tokens = 0
    total_completion_tokens = 0
    total_estimated_usd = 0.0
    total_latency_seconds = 0.0
    
    for r in records:
        op = r.entity_type or "Unknown"
        usage = r.token_usage or {}
        
        prompt_tokens = usage.get("prompt_tokens") or usage.get("input_tokens") or 0
        completion_tokens = usage.get("completion_tokens") or usage.get("output_tokens") or 0
        total_tokens = usage.get("total_tokens") or (prompt_tokens + completion_tokens)
        
        # Calculate USD cost
        if "embedding" in op.lower():
            cost = total_tokens * EMBEDDING_COST_PER_TOKEN
        else:
            cost = (prompt_tokens * GPT4O_INPUT_COST_PER_TOKEN) + (completion_tokens * GPT4O_OUTPUT_COST_PER_TOKEN)
            
        latency = r.latency or 0.0
        
        if op not in breakdown_by_operation:
            breakdown_by_operation[op] = {
                "transaction_count": 0,
                "prompt_tokens": 0,
                "completion_tokens": 0,
                "total_tokens": 0,
                "estimated_cost_usd": 0.0,
                "total_latency_sec": 0.0
            }
            
        b = breakdown_by_operation[op]
        b["transaction_count"] += 1
        b["prompt_tokens"] += prompt_tokens
        b["completion_tokens"] += completion_tokens
        b["total_tokens"] += total_tokens
        b["estimated_cost_usd"] += cost
        b["total_latency_sec"] += latency
        
        total_prompt_tokens += prompt_tokens
        total_completion_tokens += completion_tokens
        total_estimated_usd += cost
        total_latency_seconds += latency
        
    # Format per-operation averages
    operations_summary = []
    for op, data in breakdown_by_operation.items():
        count = data["transaction_count"]
        operations_summary.append({
            "operation": op,
            "transaction_count": count,
            "total_tokens": data["total_tokens"],
            "prompt_tokens": data["prompt_tokens"],
            "completion_tokens": data["completion_tokens"],
            "estimated_cost_usd": round(data["estimated_cost_usd"], 4),
            "avg_latency_sec": round(data["total_latency_sec"] / count, 3) if count > 0 else 0.0
        })
        
    return {
        "total_ai_transactions": len(records),
        "total_prompt_tokens": total_prompt_tokens,
        "total_completion_tokens": total_completion_tokens,
        "total_tokens_consumed": total_prompt_tokens + total_completion_tokens,
        "total_estimated_cost_usd": round(total_estimated_usd, 4),
        "operations": operations_summary
    }

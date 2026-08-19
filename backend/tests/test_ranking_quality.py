import pytest
import sys
import os
import json

from core.database import SessionLocal, Base, engine
from models.all_models import JobRequirement, Candidate
from services.search.eligibility import EligibilityEngine
from services.search.retrieval import HybridRetrievalEngine
from services.ai.reranker import AIReranker
from scripts.evaluate_ranking import setup_test_db, ndcg_at_k

# Ensure test DB operates cleanly
@pytest.fixture(scope="module")
def eval_db():
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    
    with open(os.path.join(os.path.dirname(os.path.dirname(__file__)), "scripts", "data", "evaluation_dataset.json"), "r") as f:
        dataset = json.load(f)
        
    setup_test_db(db, dataset)
    yield db, dataset
    db.close()

def test_minimum_ranking_quality_ndcg(eval_db):
    """
    QUALITY GATE: This test ensures that any future changes to the Retrieval 
    weights, Eligibility rules, or AI Reranker prompts do not degrade the 
    core matching quality below acceptable limits.
    """
    db, dataset = eval_db
    gt = dataset["ground_truth"]
    
    for job_data in dataset["jobs"]:
        job_id_int = int(job_data["id"].split("_")[1])
        job = db.get(JobRequirement, job_id_int)
        
        candidates = db.query(Candidate).all()
        
        # 1. Eligibility
        eligible_cands = EligibilityEngine.filter_eligible_candidates(candidates, job)
        
        # 2. Retrieval
        retriever = HybridRetrievalEngine(db)
        retrieved_cands = retriever.retrieve(job, eligible_cands, top_k=5)
        
        # 3. Reranker
        reranker = AIReranker(db)
        final_cands = reranker.evaluate_candidates(job, retrieved_cands, top_n=5)
        
        job_gt = gt.get(job_data["id"], {})
        true_scores = list(job_gt.values())
        predicted_scores = [job_gt.get(f"cand_{r['candidate_id']}", 0.0) for r in final_cands]
        
        ndcg = ndcg_at_k(predicted_scores, true_scores, 5)
        
        # The MVP requires an NDCG of at least 0.8 on the benchmark
        # If it drops below this, we've introduced a regression.
        assert ndcg >= 0.8, f"Ranking Quality Regression! NDCG for '{job.title}' dropped to {ndcg:.4f}."

def test_semantic_matching_edge_case(eval_db):
    """
    Ensures that a candidate with PyTorch (Frank) is semantically matched to a job 
    asking for TensorFlow, and that a keyword stuffer (Grace) is rejected.
    """
    db, dataset = eval_db
    job = db.query(JobRequirement).filter(JobRequirement.title == "Machine Learning Engineer").first()
    
    candidates = db.query(Candidate).all()
    eligible_cands = EligibilityEngine.filter_eligible_candidates(candidates, job)
    
    # Grace (Keyword stuffer) should be rejected due to 0 experience
    eligible_ids = [c.candidate_id for c in eligible_cands]
    
    grace = db.query(Candidate).filter(Candidate.name.like("%Grace%")).first()
    assert grace.id not in eligible_ids, "Keyword stuffer bypassed eligibility!"
    
    # Frank should be eligible
    frank = db.query(Candidate).filter(Candidate.name.like("%Frank%")).first()
    assert frank.id in eligible_ids, "Semantic candidate was falsely rejected!"

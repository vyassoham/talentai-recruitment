import json
import os
import sys
import math
from typing import List, Dict

# Ensure backend directory is in the path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy.orm import Session
from core.database import SessionLocal, Base, engine
from models.all_models import JobRequirement, Candidate, CandidateDocument, CandidateSkill, Ontology
from services.search.eligibility import EligibilityEngine
from services.search.retrieval import HybridRetrievalEngine
from services.ai.reranker import AIReranker
from services.ai.provider import get_ai_provider

def dcg_at_k(scores: List[float], k: int) -> float:
    dcg = 0.0
    for i, score in enumerate(scores[:k]):
        dcg += score / math.log2(i + 2) # i is 0-indexed, so log2(i+2) gives log2(2), log2(3)...
    return dcg

def ndcg_at_k(predicted_scores: List[float], true_scores: List[float], k: int) -> float:
    idcg = dcg_at_k(sorted(true_scores, reverse=True), k)
    if idcg == 0:
        return 0.0
    dcg = dcg_at_k(predicted_scores, k)
    return dcg / idcg

def precision_at_k(predicted_relevance: List[float], k: int, threshold: float = 0.5) -> float:
    if k == 0:
        return 0.0
    relevant = sum(1 for score in predicted_relevance[:k] if score >= threshold)
    return relevant / k

def recall_at_k(predicted_relevance: List[float], true_relevance: List[float], k: int, threshold: float = 0.5) -> float:
    total_relevant = sum(1 for score in true_relevance if score >= threshold)
    if total_relevant == 0:
        return 1.0
    retrieved_relevant = sum(1 for score in predicted_relevance[:k] if score >= threshold)
    return retrieved_relevant / total_relevant

def setup_test_db(db: Session, dataset: dict):
    from models.all_models import EvaluationEvidence, RecruiterFeedback
    # Clear DB in proper foreign key order
    db.query(EvaluationEvidence).delete()
    db.query(RecruiterFeedback).delete()
    db.query(JobRequirement).delete()
    db.query(CandidateSkill).delete()
    db.query(CandidateDocument).delete()
    db.query(Candidate).delete()
    db.query(Ontology).delete()
    db.commit()

    provider = get_ai_provider()
    
    # Setup Ontology
    ontologies = {}
    ont_id_counter = 1
    
    # Collect all unique skills
    all_skills = set()
    for job in dataset["jobs"]:
        all_skills.update(s["name"] for s in job["mandatory_skills"])
        all_skills.update(s["name"] for s in job["preferred_skills"])
    for cand in dataset["candidates"]:
        all_skills.update(cand["extracted_skills"])
        
    for skill in all_skills:
        ont = Ontology(id=ont_id_counter, canonical_name=skill, category="Skill")
        db.add(ont)
        ontologies[skill] = ont_id_counter
        ont_id_counter += 1
    db.commit()
    
    # Load Jobs
    for job_data in dataset["jobs"]:
        emb, _ = provider.generate_embeddings(job_data["raw_description"])
        
        mandatory = [{"canonical_skill_name": s["name"], "canonical_skill_id": ontologies[s["name"]], "evaluation_mode": s["mode"]} for s in job_data["mandatory_skills"]]
        preferred = [{"canonical_skill_name": s["name"], "canonical_skill_id": ontologies[s["name"]], "evaluation_mode": s["mode"]} for s in job_data["preferred_skills"]]
        
        job = JobRequirement(
            id=int(job_data["id"].split("_")[1]),
            title=job_data["title"],
            raw_description=job_data["raw_description"],
            min_experience_years=job_data["min_experience_years"],
            mandatory_skills=mandatory,
            preferred_skills=preferred,
            embedding=emb
        )
        db.add(job)
    db.commit()
    
    # Load Candidates
    for cand_data in dataset["candidates"]:
        emb, _ = provider.generate_embeddings(cand_data["cv_text"])
        cand = Candidate(
            id=int(cand_data["id"].split("_")[1]),
            name=cand_data["name"],
            total_experience_years=cand_data["total_experience_years"],
            embedding=emb
        )
        db.add(cand)
        db.flush()
        
        doc = CandidateDocument(
            candidate_id=cand.id,
            original_filename=f"{cand.name}.pdf",
            normalized_text=cand_data["cv_text"],
            sha256_hash=f"hash_{cand.id}"
        )
        db.add(doc)
        
        for skill in cand_data["extracted_skills"]:
            cs = CandidateSkill(
                candidate_id=cand.id,
                canonical_skill_id=ontologies[skill],
                original_extracted_skill=skill
            )
            db.add(cs)
            
    db.commit()

def run_evaluation():
    # Make sure tables exist
    Base.metadata.create_all(bind=engine)
    
    with open(os.path.join(os.path.dirname(__file__), "data", "evaluation_dataset.json"), "r") as f:
        dataset = json.load(f)
        
    db = SessionLocal()
    
    print("Setting up evaluation database...")
    setup_test_db(db, dataset)
    print("Database seeded.")
    
    gt = dataset["ground_truth"]
    
    for job_data in dataset["jobs"]:
        job_id_int = int(job_data["id"].split("_")[1])
        job = db.get(JobRequirement, job_id_int)
        
        print(f"\nEvaluating Job: {job.title}")
        
        candidates = db.query(Candidate).all()
        
        # 1. Eligibility
        eligible_cands = EligibilityEngine.filter_eligible_candidates(candidates, job)
        
        # 2. Hybrid Retrieval
        retriever = HybridRetrievalEngine(db)
        retrieved_cands = retriever.retrieve(job, eligible_cands, top_k=5)
        
        # 3. AI Reranking
        reranker = AIReranker(db)
        reranked_cands = reranker.evaluate_candidates(job, retrieved_cands, top_n=5)
        
        # Metrics Calculation
        job_gt = gt.get(job_data["id"], {})
        true_scores = list(job_gt.values())
        
        print("\n  --- Phase 3: Hybrid Retrieval Baseline ---")
        ret_predicted_scores = [job_gt.get(f"cand_{r['candidate_id']}", 0.0) for r in retrieved_cands]
        
        for i, r in enumerate(retrieved_cands):
            score = job_gt.get(f"cand_{r['candidate_id']}", 0.0)
            print(f"  {i+1}. {r['name']} | Retrieval Score: {r['retrieval_score']:.4f} | True Relevance: {score}")
            
        print(f"  NDCG@5:      {ndcg_at_k(ret_predicted_scores, true_scores, 5):.4f}")
        print(f"  Precision@5: {precision_at_k(ret_predicted_scores, 5):.4f}")
        print(f"  Recall@5:    {recall_at_k(ret_predicted_scores, true_scores, 5):.4f}")
        
        print("\n  --- Phase 4: AI Reranking ---")
        reranked_predicted_scores = [job_gt.get(f"cand_{r['candidate_id']}", 0.0) for r in reranked_cands]
        
        for i, r in enumerate(reranked_cands):
            score = job_gt.get(f"cand_{r['candidate_id']}", 0.0)
            print(f"  {i+1}. {r['name']} | Composite Score: {r.get('composite_score', 0.0):.4f} | True Relevance: {score}")
            
        print(f"  NDCG@5:      {ndcg_at_k(reranked_predicted_scores, true_scores, 5):.4f}")
        print(f"  Precision@5: {precision_at_k(reranked_predicted_scores, 5):.4f}")
        print(f"  Recall@5:    {recall_at_k(reranked_predicted_scores, true_scores, 5):.4f}")
        
    db.close()

if __name__ == "__main__":
    run_evaluation()

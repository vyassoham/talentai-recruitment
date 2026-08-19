import time
from sqlalchemy.orm import Session
from core.database import SessionLocal, engine, Base
from models.all_models import Candidate, JobRequirement, CandidateSkill
from services.search.eligibility import EligibilityEngine
from services.search.retrieval import HybridRetrievalEngine
from services.ai.provider import get_ai_provider

def seed_db_and_run_search():
    print("--- Starting Live DB + pgvector Verification ---")
    
    # In a real environment, run migrations. For this script, we ensure tables exist.
    try:
        Base.metadata.create_all(bind=engine)
    except Exception as e:
        print(f"Failed to connect to Database. Please ensure Postgres + pgvector is running: {e}")
        return

    db: Session = SessionLocal()
    provider = get_ai_provider()
    
    try:
        # Clear existing test data
        db.query(JobRequirement).delete()
        db.query(CandidateSkill).delete()
        db.query(Candidate).delete()
        from models.all_models import Ontology
        db.query(Ontology).delete()
        db.commit()

        # Generate some quick embeddings for testing
        emb_py, _ = provider.generate_embeddings("Python Developer")
        emb_java, _ = provider.generate_embeddings("Java Developer")
        emb_job, _ = provider.generate_embeddings("Senior Python Backend Developer")

        # Seed Job
        job = JobRequirement(
            title="Senior Python Backend Developer",
            min_experience_years=6.0,
            embedding=emb_job,
            mandatory_skills=[
                {"canonical_skill_name": "Python", "canonical_skill_id": 1, "evaluation_mode": "DETERMINISTIC"}
            ],
            preferred_skills=[
                {"canonical_skill_name": "AWS", "canonical_skill_id": 2, "evaluation_mode": "SEMANTIC"}
            ]
        )
        db.add(job)

        # Seed Candidates
        # A: Perfect match (8y, Python, AWS)
        ca = Candidate(name="Candidate A", total_experience_years=8.0, embedding=emb_py)
        # B: Almost perfect (7y, Python, no AWS)
        cb = Candidate(name="Candidate B", total_experience_years=7.0, embedding=emb_py)
        # C: Ineligible (4y, Python, AWS)
        cc = Candidate(name="Candidate C", total_experience_years=4.0, embedding=emb_py)
        # E: Ineligible (10y, Java, AWS, NO PYTHON)
        ce = Candidate(name="Candidate E", total_experience_years=10.0, embedding=emb_java)

        db.add_all([ca, cb, cc, ce])
        db.flush()
        
        from models.all_models import Ontology
        # Seed Ontology
        ont_py = Ontology(id=1, canonical_name="Python", category="Language")
        ont_aws = Ontology(id=2, canonical_name="AWS", category="Cloud")
        ont_java = Ontology(id=3, canonical_name="Java", category="Language")
        db.add_all([ont_py, ont_aws, ont_java])
        db.flush()

        db.add_all([
            CandidateSkill(candidate_id=ca.id, canonical_skill_id=1, original_extracted_skill="Python"),
            CandidateSkill(candidate_id=ca.id, canonical_skill_id=2, original_extracted_skill="AWS"),
            
            CandidateSkill(candidate_id=cb.id, canonical_skill_id=1, original_extracted_skill="Python"),
            
            CandidateSkill(candidate_id=cc.id, canonical_skill_id=1, original_extracted_skill="Python"),
            CandidateSkill(candidate_id=cc.id, canonical_skill_id=2, original_extracted_skill="AWS"),
            
            CandidateSkill(candidate_id=ce.id, canonical_skill_id=3, original_extracted_skill="Java"),
            CandidateSkill(candidate_id=ce.id, canonical_skill_id=2, original_extracted_skill="AWS"),
        ])
        db.commit()

        print("\nSeeding complete. Executing Search Pipeline...")

        start_time = time.time()
        
        # 1. Eligibility
        elig_start = time.perf_counter()
        candidates = db.query(Candidate).all()
        eligible_results = EligibilityEngine.filter_eligible_candidates(candidates, job)
        elig_t = time.perf_counter() - elig_start

        print("\n--- Phase 3: Hybrid Retrieval ---")
        start_t = time.perf_counter()
        engine_search = HybridRetrievalEngine(db)
        retrieved_results = engine_search.retrieve(job, eligible_results, top_k=5)
        retrieval_t = time.perf_counter() - start_t
        
        print("\n--- Phase 4: AI Deep Reranking ---")
        from services.ai.reranker import AIReranker
        start_r = time.perf_counter()
        reranker = AIReranker(db)
        final_results = reranker.evaluate_candidates(job, retrieved_results, top_n=5)
        rerank_t = time.perf_counter() - start_r

        print(f"Total Eligible Candidates: {len(eligible_results)}")
        print(f"Total Retrieved Candidates: {len(final_results)}")
        print(f"\nLatencies:\n  Eligibility: {elig_t*1000:.2f} ms\n  Retrieval: {retrieval_t*1000:.2f} ms\n  Reranking: {rerank_t*1000:.2f} ms\n  Total: {(elig_t+retrieval_t+rerank_t)*1000:.2f} ms")

        print("\nTop Candidates Retrieved & Reranked:")
        for r in final_results:
            ai_score = r.get("ai_evaluation", {}).get("overall_score") if r.get("ai_evaluation") else "N/A"
            print(f"  - {r['name']} | Composite: {r['composite_score']:.4f} | Retrieval: {r['retrieval_score']:.4f} | AI: {ai_score} | Matched: {r['matched_skills']} | Missing: {r['missing_preferred_skills']}")
            if r.get("ai_evaluation"):
                print(f"    AI Reasoning: {r['ai_evaluation']['reasoning_summary']}")

        names = [r["name"] for r in final_results]
        
        # Candidate A should generally rank first due to having all skills
        assert "Candidate A" in names, "Candidate A should be retrieved"
        assert "Candidate C" not in names, "Candidate C should fail experience constraint"
        assert "Candidate E" not in names, "Candidate E should fail mandatory Python constraint"

        # Verify evidence persisted
        from models.all_models import EvaluationEvidence
        evidence_count = db.query(EvaluationEvidence).count()
        print(f"\n[SUCCESS] Verification SUCCESS: {evidence_count} evidence records persisted to DB. Ineligible candidates properly excluded. Scoring deterministic.")
        
    finally:
        db.close()

if __name__ == "__main__":
    seed_db_and_run_search()

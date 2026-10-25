import pytest
from unittest.mock import MagicMock
from models.all_models import Candidate, JobRequirement, CandidateSkill
from services.search.eligibility import CandidateEligibilityResult
from services.search.retrieval import HybridRetrievalEngine

def test_retrieval_reuses_preloaded_candidates_without_db_query():
    mock_db = MagicMock()
    
    # 1. Prepare candidates in memory (simulating pre-filtered candidates in routes_search.py)
    c1 = Candidate(
        id=1,
        name="Candidate 1",
        total_experience_years=5.0,
        skills=[CandidateSkill(canonical_skill_id=10, original_extracted_skill="Python")],
        documents=[],
        embedding=None
    )
    c2 = Candidate(
        id=2,
        name="Candidate 2",
        total_experience_years=3.0,
        skills=[],
        documents=[],
        embedding=None
    )
    preloaded_candidates = [c1, c2]

    job = JobRequirement(
        id=1,
        title="Python Dev",
        mandatory_skills=[{"canonical_skill_id": 10, "canonical_skill_name": "Python"}],
        preferred_skills=[],
        embedding=None
    )

    eligible_results = [
        CandidateEligibilityResult(candidate_id=1, eligible=True, requirements=[])
    ]

    engine = HybridRetrievalEngine(mock_db)

    # 2. Call retrieve WITH candidates=preloaded_candidates
    results = engine.retrieve(job, eligible_results, top_k=10, candidates=preloaded_candidates)

    # 3. VERIFY: results returned correctly
    assert len(results) == 1
    assert results[0]["candidate_id"] == "1"

    # 4. CRITICAL CHECK: Ensure mock_db.query(Candidate) was NEVER called!
    # Because preloaded candidates were reused, there should be ZERO queries against Candidate
    query_calls = [call for call in mock_db.query.mock_calls if len(call.args) > 0 and call.args[0] == Candidate]
    assert len(query_calls) == 0, f"Expected 0 Candidate queries, found {len(query_calls)}"

def test_retrieval_fallback_queries_db_when_candidates_none():
    mock_db = MagicMock()
    c1 = Candidate(
        id=1,
        name="Candidate 1",
        total_experience_years=5.0,
        skills=[],
        documents=[],
        embedding=None
    )
    mock_db.query().options().filter().all.return_value = [c1]

    job = JobRequirement(id=1, title="Dev", mandatory_skills=[], preferred_skills=[], embedding=None)
    eligible_results = [CandidateEligibilityResult(candidate_id=1, eligible=True, requirements=[])]

    engine = HybridRetrievalEngine(mock_db)
    results = engine.retrieve(job, eligible_results, top_k=10, candidates=None)

    assert len(results) == 1
    # Fallback correctly queries DB
    assert mock_db.query.called

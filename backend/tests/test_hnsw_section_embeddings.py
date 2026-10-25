import pytest
from unittest.mock import MagicMock
from models.all_models import Candidate, CandidateSectionEmbedding, JobRequirement
from services.search.eligibility import CandidateEligibilityResult
from services.search.retrieval import HybridRetrievalEngine

def test_models_have_hnsw_indexes_configured():
    # Verify Candidate table args
    cand_indexes = {idx.name: idx for idx in Candidate.__table_args__}
    assert "ix_candidates_embedding_hnsw" in cand_indexes
    hnsw_cand = cand_indexes["ix_candidates_embedding_hnsw"]
    assert hnsw_cand.dialect_kwargs.get("postgresql_using") == "hnsw"

    # Verify CandidateSectionEmbedding table args
    sec_indexes = {idx.name: idx for idx in CandidateSectionEmbedding.__table_args__}
    assert "ix_candidate_section_embeddings_hnsw" in sec_indexes
    hnsw_sec = sec_indexes["ix_candidate_section_embeddings_hnsw"]
    assert hnsw_sec.dialect_kwargs.get("postgresql_using") == "hnsw"

def test_empty_section_embeddings_table_skips_query():
    mock_db = MagicMock()
    # Reset cached flag to None to force check
    HybridRetrievalEngine._HAS_SECTION_EMBEDDINGS = None

    # Simulate empty table on first check: .first() returns None
    mock_db.query(CandidateSectionEmbedding.id).first.return_value = None

    c1 = Candidate(id=1, total_experience_years=3.0, skills=[], documents=[], embedding=[0.1]*1536)
    job = JobRequirement(id=1, title="Dev", mandatory_skills=[], preferred_skills=[], embedding=[0.1]*1536)
    elig = [CandidateEligibilityResult(candidate_id=1, eligible=True, requirements=[])]

    engine = HybridRetrievalEngine(mock_db)
    results = engine.retrieve(job, elig, top_k=5, candidates=[c1])

    assert len(results) == 1
    # Check that CandidateSectionEmbedding vector distance was never queried
    calls_for_sec_distance = [
        call for call in mock_db.query.mock_calls 
        if any(isinstance(arg, type) and issubclass(arg, CandidateSectionEmbedding) for arg in call.args if hasattr(arg, '__mro__'))
    ]
    assert len(calls_for_sec_distance) == 0, "Expected 0 queries to empty CandidateSectionEmbedding"

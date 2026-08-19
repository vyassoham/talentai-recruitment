import pytest
from unittest.mock import MagicMock
from services.ai.reranker import AIReranker, CandidateEvaluation, RequirementAssessment

def test_ai_reranker_success():
    mock_db = MagicMock()
    mock_job = MagicMock()
    mock_job.id = 1
    mock_job.title = "Test Job"
    
    mock_doc = MagicMock()
    mock_doc.normalized_text = "Experienced Python Developer"
    mock_db.query().filter().first.return_value = mock_doc
    
    mock_candidate = MagicMock()
    mock_candidate.external_evidence = None
    mock_db.get.return_value = mock_candidate
    
    # Mock Provider
    class DummyProvider:
        def generate_structured(self, p, s, sp):
            return CandidateEvaluation(
                overall_score=0.9,
                reasoning_summary="Great fit",
                assessments=[
                    RequirementAssessment(
                        requirement="Python",
                        evidence="Experienced Python Developer",
                        assessment="Meets",
                        confidence=0.95
                    )
                ]
            ), {"prompt_tokens": 10, "completion_tokens": 10}
            
        @property
        def model_name(self): return "dummy"
        
    reranker = AIReranker(mock_db)
    reranker.provider = DummyProvider()
    
    candidates = [
        {"candidate_id": 1, "retrieval_score": 0.8},
        {"candidate_id": 2, "retrieval_score": 0.5}
    ]
    
    result = reranker.evaluate_candidates(mock_job, candidates, top_n=1)
    
    # Candidate 1 evaluated
    assert result[0]["candidate_id"] == 1
    assert result[0]["ai_evaluation"]["overall_score"] == 0.9
    assert result[0]["composite_score"] == (0.8 * 0.3) + (0.9 * 0.7)
    
    # Candidate 2 not evaluated (top_n=1 fallback)
    assert result[1]["candidate_id"] == 2
    assert result[1]["ai_evaluation"] is None
    assert result[1]["composite_score"] == (0.5 * 0.3)
    
    # DB calls
    assert mock_db.add.call_count == 2 # 1 Evidence + 1 Registry
    mock_db.commit.assert_called_once()

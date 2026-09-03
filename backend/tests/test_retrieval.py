import pytest
from unittest.mock import MagicMock
from services.search.retrieval import HybridRetrievalEngine
from services.search.eligibility import CandidateEligibilityResult
from models.all_models import Candidate, JobRequirement, CandidateSkill

def test_hybrid_retrieval_scoring():
    mock_db = MagicMock()
    
    job = JobRequirement(
        id=1,
        embedding=[0.1, 0.2, 0.3], # dummy 3D for test math
        mandatory_skills=[
            {"canonical_skill_id": 1, "canonical_skill_name": "Python"}
        ],
        preferred_skills=[
            {"canonical_skill_id": 2, "canonical_skill_name": "AWS"}
        ]
    )
    
    # Perfect candidate
    c1 = Candidate(
        id=1, 
        total_experience_years=10.0,
        embedding=[0.1, 0.2, 0.3], 
        skills=[
            CandidateSkill(canonical_skill_id=1, original_extracted_skill="Python"),
            CandidateSkill(canonical_skill_id=2, original_extracted_skill="AWS")
        ]
    )
    
    # Partial candidate (no AWS)
    c2 = Candidate(
        id=2, 
        total_experience_years=5.0,
        embedding=[0.0, 0.0, 0.0], # Orthogonal / Bad semantic
        skills=[
            CandidateSkill(canonical_skill_id=1, original_extracted_skill="Python")
        ]
    )
    
    mock_db.query().filter().all.return_value = [c1, c2]
    mock_db.query().options().filter().all.return_value = [c1, c2]
    
    engine = HybridRetrievalEngine(mock_db)
    
    eligible = [
        CandidateEligibilityResult(candidate_id=1, eligible=True, requirements=[]),
        CandidateEligibilityResult(candidate_id=2, eligible=True, requirements=[])
    ]
    
    results = engine.retrieve(job, eligible, top_k=10)
    
    assert len(results) == 2
    assert results[0]["candidate_id"] == "1" # Should score highest
    
    # c1 check
    assert results[0]["skill_match_score"] == 1.0 # 100% mandatory overlap
    assert "AWS" in results[0]["matched_skills"]
    assert results[0]["experience_signal"] == 1.0 # 10/10 max
    
    # c2 check
    assert results[1]["candidate_id"] == "2"
    assert "AWS" in results[1]["missing_preferred_skills"]
    assert results[1]["experience_signal"] == 0.5 # 5/10 max

def test_candidate_section_chunking():
    from services.ai.embeddings import EmbeddingsService
    from models.all_models import Employment
    
    cand = Candidate(
        id=10,
        name="Alice Tech",
        current_title="Lead Architect",
        total_experience_years=8.0,
        location="San Francisco",
        skills=[
            CandidateSkill(original_extracted_skill="Python"),
            CandidateSkill(original_extracted_skill="Kubernetes")
        ],
        employments=[
            Employment(
                job_title="Senior DevOps",
                company="CloudTech",
                description="Engineered Kubernetes clusters with Helm.",
                extracted_skills=["Kubernetes", "Helm", "Docker"]
            )
        ],
        external_evidence="GitHub: 50+ repositories in distributed systems."
    )
    
    chunks = EmbeddingsService.chunk_candidate_sections(cand)
    types = [c["section_type"] for c in chunks]
    
    assert "SUMMARY" in types
    assert "SKILLS" in types
    assert "EXPERIENCE" in types
    assert "ENRICHMENT" in types
    
    # Check that skills chunk contains the actual extracted skills
    skills_chunk = next(c for c in chunks if c["section_type"] == "SKILLS")
    assert "Python" in skills_chunk["content_chunk"]
    assert "Kubernetes" in skills_chunk["content_chunk"]
    
    # Check that experience chunk contains role & company
    exp_chunk = next(c for c in chunks if c["section_type"] == "EXPERIENCE")
    assert "Senior DevOps" in exp_chunk["content_chunk"]
    assert "CloudTech" in exp_chunk["content_chunk"]


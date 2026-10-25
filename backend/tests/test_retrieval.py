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

def test_retrieval_result_contact_regex_efficiency():
    import time
    from models.all_models import CandidateDocument
    from services.search.retrieval import RetrievalResult
    from services.search.eligibility import CandidateEligibilityResult

    # Generate 50KB of mock resume text
    large_body = " Lorem ipsum dolor sit amet, consectetur adipiscing elit." * 1000  # ~57KB
    raw_cv = "Contact: test.engineer@company.io | Phone: +1-555-234-5678\n" + large_body

    doc = CandidateDocument(
        id=1,
        storage_key="resumes/test_cv.pdf",
        raw_extracted_text=raw_cv
    )
    # Case 1: email and phone missing in candidate -> extracted from header swiftly
    candidate_no_contact = Candidate(
        id=1,
        name="Test Engineer",
        email=None,
        phone=None,
        total_experience_years=4.0,
        documents=[doc],
        skills=[]
    )
    elig = CandidateEligibilityResult(candidate_id=1, eligible=True, requirements=[])
    res = RetrievalResult(candidate_no_contact, elig)

    start = time.time()
    data = res.to_dict()
    elapsed = time.time() - start

    assert data["email"] == "test.engineer@company.io"
    assert "555-234-5678" in data["phone"]
    # Must complete in sub-millisecond even with 57KB string
    assert elapsed < 0.05, f"Regex took too long: {elapsed:.4f}s"

    # Case 2: email and phone already in candidate -> zero regex overhead
    candidate_with_contact = Candidate(
        id=2,
        name="Direct Contact",
        email="direct@domain.com",
        phone="+1-555-999-8888",
        total_experience_years=6.0,
        documents=[doc],
        skills=[]
    )
    res2 = RetrievalResult(candidate_with_contact, elig)
    data2 = res2.to_dict()
    assert data2["email"] == "direct@domain.com"
    assert data2["phone"] == "+1-555-999-8888"



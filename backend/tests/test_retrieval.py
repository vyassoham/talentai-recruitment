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

def test_multi_vector_section_highlighting():
    from models.all_models import CandidateSectionEmbedding
    from services.search.retrieval import RetrievalResult
    from services.search.eligibility import CandidateEligibilityResult

    mock_db = MagicMock()
    job = JobRequirement(
        id=1,
        embedding=[0.5, 0.5, 0.5],
        mandatory_skills=[{"canonical_skill_name": "Python"}],
        preferred_skills=[]
    )
    
    cand = Candidate(
        id=42,
        name="Vector Specialist",
        current_title="Principal Engineer",
        current_company="AI Cloud Inc",
        total_experience_years=7.0,
        skills=[CandidateSkill(original_extracted_skill="Python")]
    )

    # Mock CandidateSectionEmbedding query result
    mock_sec1 = MagicMock()
    mock_sec1.candidate_id = 42
    mock_sec1.distance = 0.15 # 0.85 similarity
    mock_sec1.section_title = "Principal Engineer at AI Cloud Inc"
    mock_sec1.section_type = "EXPERIENCE"
    mock_sec1.content_chunk = "Led Python microservices architecture using pgvector, FastAPI and Kafka for high-scale search."

    mock_sec2 = MagicMock()
    mock_sec2.candidate_id = 42
    mock_sec2.distance = 0.28 # 0.72 similarity
    mock_sec2.section_title = "Core Technical Skills & Stack"
    mock_sec2.section_type = "SKILLS"
    mock_sec2.content_chunk = "Technical Skills & Tooling: Python, PostgreSQL, Kafka, Redis, Docker"

    # Engine with mocked section records
    HybridRetrievalEngine.notify_section_embeddings_created()
    engine = HybridRetrievalEngine(mock_db)

    # Configure query chain
    mock_db.query.return_value.filter.return_value.all.side_effect = [
        [], # RecruiterFeedback
        [], # Global candidate dist_records
        [mock_sec1, mock_sec2] # Section dist_records
    ]

    elig = [CandidateEligibilityResult(candidate_id=42, eligible=True, requirements=[])]
    results = engine.retrieve(job, elig, top_k=5, candidates=[cand])

    assert len(results) == 1
    top_cand = results[0]
    
    # Verify highlighted_section is populated with highest similarity
    assert top_cand["highlighted_section"] is not None
    assert top_cand["highlighted_section"]["section_title"] == "Principal Engineer at AI Cloud Inc"
    assert top_cand["highlighted_section"]["section_type"] == "EXPERIENCE"
    assert "pgvector, FastAPI and Kafka" in top_cand["highlighted_section"]["content_chunk"]
    assert top_cand["highlighted_section"]["similarity_score"] == 0.85

    # Verify matched_sections list has both sections in descending similarity order
    assert len(top_cand["matched_sections"]) == 2
    assert top_cand["matched_sections"][0]["similarity_score"] >= top_cand["matched_sections"][1]["similarity_score"]
    assert top_cand["matched_sections"][1]["section_type"] == "SKILLS"




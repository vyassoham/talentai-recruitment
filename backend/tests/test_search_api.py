import pytest
from fastapi.testclient import TestClient
from main import app
from core.database import get_db
from core.auth import get_current_user
from models.all_models import User, UserRole
from unittest.mock import MagicMock, patch
from services.ai.reranker import CandidateEvaluation, RequirementAssessment

client = TestClient(app)

def test_search_candidates_api():
    mock_db = MagicMock()
    
    # Needs a mock job
    mock_job = MagicMock()
    mock_job.mandatory_skills = []
    mock_job.preferred_skills = []
    mock_job.embedding = None
    mock_job.min_experience_years = 2.0
    mock_db.get.return_value = mock_job
    
    # Needs mock candidates
    mock_c = MagicMock()
    mock_c.id = 1
    mock_c.name = "Test"
    mock_c.total_experience_years = 5.0
    mock_c.skills = []
    mock_c.embedding = None
    
    # Configure mock query chain
    mock_db.query().all.return_value = [mock_c]
    mock_db.query().filter().all.return_value = [mock_c]
    mock_db.query().options().all.return_value = [mock_c]
    mock_db.query().options().filter().all.return_value = [mock_c]

    # Mock user with RECRUITER role
    mock_user = User(id=1, email="recruiter@test.com", role=UserRole.RECRUITER.value, is_active=True)

    app.dependency_overrides[get_db] = lambda: mock_db
    app.dependency_overrides[get_current_user] = lambda: mock_user

    response = client.post(
        "/api/v1/candidates/search", 
        json={"job_id": "1", "top_k": 10},
        headers={"X-API-Key": "dev-secret-api-key"}
    )
    
    assert response.status_code == 200
    data = response.json()
    assert data["job_id"] == "1"
    assert data["eligible_count"] == 1
    assert data["retrieved_count"] == 1
    assert "telemetry" in data
    assert len(data["candidates"]) == 1
    assert data["candidates"][0]["name"] == "Test"
    
    app.dependency_overrides.clear()

def test_evaluate_candidate_api():
    mock_db = MagicMock()
    
    mock_job = MagicMock()
    mock_job.id = 1
    mock_job.title = "Test Job"
    mock_job.raw_description = "Job desc"
    mock_job.mandatory_skills = []
    mock_job.preferred_skills = []
    
    mock_cand = MagicMock()
    mock_cand.id = 1
    mock_cand.name = "Test Candidate"
    mock_cand.current_title = "Developer"
    mock_cand.total_experience_years = 4.0
    mock_cand.location = "Remote"
    mock_cand.current_company = "Tech"
    mock_cand.skills = []
    mock_cand.external_evidence = None

    mock_doc = MagicMock()
    mock_doc.normalized_text = "Developer CV text"
    
    def mock_get(model, obj_id):
        if model.__name__ == "JobRequirement":
            return mock_job
        elif model.__name__ == "Candidate":
            return mock_cand
        return None
        
    mock_db.get = mock_get
    mock_db.query().filter().first.return_value = mock_doc
    mock_db.query().order_by().first.return_value = mock_job

    mock_user = User(id=1, email="recruiter@test.com", role=UserRole.RECRUITER.value, is_active=True)

    app.dependency_overrides[get_db] = lambda: mock_db
    app.dependency_overrides[get_current_user] = lambda: mock_user

    mock_provider = MagicMock()
    mock_provider.model_name = "test-model"
    mock_provider.generate_structured.return_value = (
        CandidateEvaluation(
            overall_score=0.88,
            reasoning_summary="Strong technical fit",
            key_strengths=["Python", "FastAPI"],
            hiring_verdict="Highly Recommended",
            assessments=[
                RequirementAssessment(
                    requirement="Python",
                    evidence="Developer CV text",
                    assessment="Meets",
                    confidence=0.95
                )
            ]
        ),
        {"prompt_tokens": 100, "completion_tokens": 50}
    )

    with patch("services.ai.reranker.get_ai_provider", return_value=mock_provider):
        response = client.post(
            "/api/v1/candidates/1/evaluate",
            json={"job_id": "1"},
            headers={"X-API-Key": "dev-secret-api-key"}
        )
    
    assert response.status_code == 200
    data = response.json()
    assert data["candidate_id"] == 1
    assert "ai_evaluation" in data
    assert data["ai_evaluation"]["overall_score"] == 0.88
    assert data["ai_evaluation"]["hiring_verdict"] == "Highly Recommended"
    
    app.dependency_overrides.clear()

def test_candidate_resume_preview_api():
    mock_db = MagicMock()
    mock_cand = MagicMock()
    mock_cand.id = 1
    mock_cand.name = "Test Candidate"
    mock_cand.current_title = "Senior Python Engineer"
    mock_cand.email = "test@example.com"
    mock_cand.phone = "+1 555-0199"
    mock_cand.location = "Remote"
    mock_cand.total_experience_years = 5.0
    mock_cand.current_company = "TechCorp"
    mock_cand.skills = []
    mock_cand.employments = []
    mock_cand.external_evidence = None

    mock_doc = MagicMock()
    mock_doc.normalized_text = "Experienced Senior Python Engineer with 5 years in backend systems."
    mock_doc.storage_key = "non_existent_old_file.pdf"
    
    mock_db.get.return_value = mock_cand
    mock_db.query().filter().first.return_value = mock_doc

    mock_user = User(id=1, email="recruiter@test.com", role=UserRole.RECRUITER.value, is_active=True)

    app.dependency_overrides[get_db] = lambda: mock_db
    app.dependency_overrides[get_current_user] = lambda: mock_user

    response = client.get("/api/v1/candidates/1/resume")
    assert response.status_code == 200
    assert response.headers["content-type"] == "application/pdf"
    assert response.content.startswith(b"%PDF-")
    assert len(response.content) > 500

    app.dependency_overrides.clear()

import pytest
from fastapi.testclient import TestClient
from main import app
from core.database import get_db
from core.auth import get_current_user
from models.all_models import User, UserRole
from unittest.mock import MagicMock

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

    response = client.post("/api/v1/candidates/search", json={"job_id": "1", "top_k": 10})
    
    assert response.status_code == 200
    data = response.json()
    assert data["job_id"] == "1"
    assert data["eligible_count"] == 1
    assert data["retrieved_count"] == 1
    assert "telemetry" in data
    assert len(data["candidates"]) == 1
    assert data["candidates"][0]["name"] == "Test"
    
    app.dependency_overrides.clear()

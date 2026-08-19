import pytest
from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient
from main import app
from core.database import get_db
from core.auth import get_current_user
from models.all_models import User, UserRole, Candidate

client = TestClient(app)

@pytest.fixture
def auth_recruiter():
    mock_user = User(id=1, email="recruiter@test.com", role=UserRole.RECRUITER.value, is_active=True)
    app.dependency_overrides[get_current_user] = lambda: mock_user
    yield mock_user
    app.dependency_overrides.clear()

def test_sourcing_github_success(auth_recruiter):
    mock_discovered = [
        {
            "name": "Dev Alice",
            "email": "alice@github.com",
            "location": "San Francisco",
            "github_url": "https://github.com/alice",
            "source": "GITHUB_SOURCING"
        }
    ]
    
    with patch("services.enrichment.passive_sourcer.PassiveSourcer.search_github", return_value=mock_discovered), \
         patch("services.enrichment.passive_sourcer.PassiveSourcer.ingest_discovered_candidates", return_value={"created": 1, "skipped_duplicates": 0}):
        
        response = client.post("/api/v1/sourcing/github", json={
            "language": "Python",
            "location": "San Francisco",
            "min_repos": 5,
            "max_results": 10
        })
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "SUCCESS"
        assert data["candidates_discovered"] == 1
        assert data["candidates_created"] == 1

def test_sourcing_github_no_results(auth_recruiter):
    with patch("services.enrichment.passive_sourcer.PassiveSourcer.search_github", return_value=[]):
        response = client.post("/api/v1/sourcing/github", json={
            "language": "ObscureLang",
            "min_repos": 50
        })
        assert response.status_code == 200
        assert response.json()["status"] == "NO_RESULTS"

def test_sourcing_stackoverflow_success(auth_recruiter):
    mock_discovered = [
        {
            "name": "Expert Bob",
            "reputation": 15000,
            "primary_tag": "python",
            "source": "STACKOVERFLOW_SOURCING"
        }
    ]
    
    with patch("services.enrichment.passive_sourcer.PassiveSourcer.search_stackoverflow", return_value=mock_discovered), \
         patch("services.enrichment.passive_sourcer.PassiveSourcer.ingest_discovered_candidates", return_value={"created": 1, "skipped_duplicates": 0}):
        
        response = client.post("/api/v1/sourcing/stackoverflow", json={
            "tags": ["python", "fastapi"],
            "min_reputation": 1000
        })
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "SUCCESS"
        assert data["candidates_discovered"] == 1

def test_sourcing_stale_profiles_endpoint(auth_recruiter):
    mock_stale = [
        {"candidate_id": 1, "name": "Charlie", "staleness_score": 0.8}
    ]
    with patch("services.enrichment.staleness_checker.get_stale_candidates", return_value=mock_stale):
        response = client.get("/api/v1/sourcing/stale-profiles?threshold_days=60")
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 1
        assert data["stale_profiles"][0]["name"] == "Charlie"

def test_sourcing_trigger_stale_refresh(auth_recruiter):
    with patch("services.enrichment.staleness_checker.refresh_stale_profiles", return_value={"stale_found": 5, "enqueued": 3}):
        response = client.post("/api/v1/sourcing/refresh-stale?threshold_days=90")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "REFRESH_INITIATED"
        assert data["enqueued"] == 3

def test_manual_enrichment_candidate_not_found(auth_recruiter):
    mock_db = MagicMock()
    mock_db.get.return_value = None
    app.dependency_overrides[get_db] = lambda: mock_db

    response = client.post("/api/v1/sourcing/enrich/99999")
    assert response.status_code == 404
    assert response.json()["detail"] == "Candidate not found"

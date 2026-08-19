import pytest
from fastapi.testclient import TestClient
from unittest.mock import MagicMock
from main import app
from core.database import get_db
from core.auth import get_current_user
from models.all_models import User, UserRole, AIRegistry

client = TestClient(app)

def test_dei_analytics_calculation():
    mock_db = MagicMock()
    
    # Mock base demographics query (gender, race, count)
    mock_base_stats = [
        ("Female", "Asian", 10),
        ("Male", "Asian", 20),
        ("Female", "Black/African American", 15),
        ("Male", "Caucasian", 25),
    ]
    
    # Mock passed AI query (gender, race, pass_count)
    mock_pass_stats = [
        ("Female", "Asian", 8),    # 80% pass rate
        ("Male", "Asian", 16),     # 80% pass rate
        ("Female", "Black/African American", 12), # 80% pass rate
        ("Male", "Caucasian", 20),  # 80% pass rate
    ]

    mock_db.query().group_by().all.return_value = mock_base_stats
    mock_db.query().join().filter().group_by().all.return_value = mock_pass_stats

    mock_user = User(id=1, email="recruiter@test.com", role=UserRole.RECRUITER.value, is_active=True)

    app.dependency_overrides[get_db] = lambda: mock_db
    app.dependency_overrides[get_current_user] = lambda: mock_user

    response = client.get("/api/v1/analytics/dei")
    assert response.status_code == 200
    
    data = response.json()
    assert "dei_analytics" in data
    report = data["dei_analytics"]
    assert len(report) == 4
    
    for entry in report:
        assert entry["pass_rate_percentage"] == 80.0
        assert entry["total_applicants"] > 0
        assert entry["passed_ai"] > 0

    app.dependency_overrides.clear()

def test_dei_analytics_empty_demographics():
    mock_db = MagicMock()
    mock_db.query().group_by().all.return_value = []
    mock_db.query().join().filter().group_by().all.return_value = []

    mock_user = User(id=1, email="recruiter@test.com", role=UserRole.RECRUITER.value, is_active=True)

    app.dependency_overrides[get_db] = lambda: mock_db
    app.dependency_overrides[get_current_user] = lambda: mock_user

    response = client.get("/api/v1/analytics/dei")
    assert response.status_code == 200
    assert response.json() == {"dei_analytics": []}

    app.dependency_overrides.clear()

def test_ai_cost_analytics_aggregation():
    mock_db = MagicMock()
    
    r1 = AIRegistry(
        entity_type="CV_PARSER",
        latency=1.2,
        token_usage={"prompt_tokens": 1500, "completion_tokens": 400, "total_tokens": 1900}
    )
    r2 = AIRegistry(
        entity_type="CandidateEvaluation",
        latency=0.8,
        token_usage={"prompt_tokens": 800, "completion_tokens": 250, "total_tokens": 1050}
    )
    
    mock_db.query(AIRegistry).all.return_value = [r1, r2]

    mock_user = User(id=1, email="recruiter@test.com", role=UserRole.RECRUITER.value, is_active=True)

    app.dependency_overrides[get_db] = lambda: mock_db
    app.dependency_overrides[get_current_user] = lambda: mock_user

    response = client.get("/api/v1/analytics/ai-costs")
    assert response.status_code == 200
    data = response.json()
    
    assert data["total_ai_transactions"] == 2
    assert data["total_prompt_tokens"] == 2300
    assert data["total_completion_tokens"] == 650
    assert data["total_tokens_consumed"] == 2950
    assert data["total_estimated_cost_usd"] > 0
    assert len(data["operations"]) == 2

    app.dependency_overrides.clear()

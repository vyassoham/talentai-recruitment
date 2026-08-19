import pytest
from fastapi.testclient import TestClient
from main import app
from core.auth import AuthUtils
from core.database import get_db
from models.all_models import User, UserRole
from unittest.mock import MagicMock

client = TestClient(app)

def test_unauthenticated_requests_blocked():
    # 1. Search requires authentication
    res = client.post("/api/v1/candidates/search", json={"job_id": "1"})
    assert res.status_code == 401
    
    # 2. JD Parsing requires authentication
    res = client.post("/api/v1/jobs/parse", json={"job_description": "Python Developer"})
    assert res.status_code == 401
    
    # 3. Sourcing requires authentication
    res = client.post("/api/v1/sourcing/github", json={"language": "python"})
    assert res.status_code == 401
    
    # 4. DEI Analytics requires authentication
    res = client.get("/api/v1/analytics/dei")
    assert res.status_code == 401

def test_authenticated_recruiter_token_flow():
    mock_db = MagicMock()
    
    # Mock user
    hashed = AuthUtils.get_password_hash("secure_password")
    mock_user = User(id=1, email="recruiter@company.com", hashed_password=hashed, role=UserRole.RECRUITER.value, is_active=True)
    mock_db.query().filter().first.return_value = mock_user
    
    app.dependency_overrides[get_db] = lambda: mock_db
    
    # Login to get token
    login_res = client.post("/api/v1/auth/token", data={"username": "recruiter@company.com", "password": "secure_password"})
    assert login_res.status_code == 200
    token = login_res.json()["access_token"]
    
    # Test DEI Analytics with Bearer Token
    mock_db.query().group_by().all.return_value = []
    auth_headers = {"Authorization": f"Bearer {token}"}
    dei_res = client.get("/api/v1/analytics/dei", headers=auth_headers)
    assert dei_res.status_code == 200
    
    app.dependency_overrides.clear()

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


def test_default_admin_password_rejected():
    """Verify that the vulnerable default password 'admin_password' is rejected."""
    res = client.post("/api/v1/auth/token", data={"username": "admin@recruit.ai", "password": "admin_password"})
    assert res.status_code == 401
    assert "Incorrect email or password" in res.json().get("detail", "")


def test_secure_admin_password_accepted():
    """Verify that the rotated admin password authenticates successfully."""
    import os
    from core.config import settings
    admin_pw = getattr(settings, "ADMIN_PASSWORD", None) or os.getenv("ADMIN_PASSWORD")
    if not admin_pw:
        pytest.skip("ADMIN_PASSWORD not set in environment")
    res = client.post("/api/v1/auth/token", data={"username": "admin@recruit.ai", "password": admin_pw})
    assert res.status_code == 200
    data = res.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"


def test_dev_secret_api_key_rejected_in_production(monkeypatch):
    """Verify that default 'dev-secret-api-key' is rejected in production environment."""
    from core.config import settings
    monkeypatch.setattr(settings, "ENVIRONMENT", "production")
    monkeypatch.setattr(settings, "SECRET_API_KEY", "dev-secret-api-key")
    monkeypatch.setenv("SECRET_API_KEY", "dev-secret-api-key")
    
    # Try accessing with dev-secret-api-key header
    headers = {"X-API-Key": "dev-secret-api-key"}
    res = client.get("/api/v1/analytics/dei", headers=headers)
    assert res.status_code == 403
    assert "prohibited in production" in res.json().get("detail", "")


def test_seed_admin_disabled_in_production(monkeypatch):
    """Verify seed-admin endpoint cannot be called in production."""
    from core.config import settings
    monkeypatch.setattr(settings, "ENVIRONMENT", "production")
    res = client.post("/api/v1/auth/seed-admin")
    assert res.status_code == 403


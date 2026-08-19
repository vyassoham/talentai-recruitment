import pytest
from datetime import timedelta
from fastapi.testclient import TestClient
from fastapi import HTTPException
from unittest.mock import MagicMock
import jwt

from main import app
from core.auth import AuthUtils, get_current_user, require_role, SECRET_KEY, ALGORITHM
from core.database import get_db
from models.all_models import User, UserRole

client = TestClient(app)

def test_password_hashing_and_verification():
    raw_password = "SecureRecruiterPassword2026!"
    hashed = AuthUtils.get_password_hash(raw_password)
    
    assert hashed != raw_password
    assert AuthUtils.verify_password(raw_password, hashed) is True
    assert AuthUtils.verify_password("WrongPassword", hashed) is False

def test_jwt_token_expiration():
    # Generate an expired token
    expired_token = AuthUtils.create_access_token(
        data={"sub": "user@test.com"}, 
        expires_delta=timedelta(seconds=-10)
    )
    
    mock_db = MagicMock()
    with pytest.raises(HTTPException) as exc_info:
        get_current_user(token=expired_token, db=mock_db)
    
    assert exc_info.value.status_code == 401
    assert exc_info.value.detail == "Could not validate credentials"

def test_jwt_tampered_token():
    valid_token = AuthUtils.create_access_token(data={"sub": "user@test.com"})
    tampered_token = valid_token[:-4] + "abcd"
    
    mock_db = MagicMock()
    with pytest.raises(HTTPException) as exc_info:
        get_current_user(token=tampered_token, db=mock_db)
        
    assert exc_info.value.status_code == 401

def test_role_authorization_enforcement():
    recruiter_checker = require_role("RECRUITER")
    
    # 1. Recruiter user passes
    recruiter_user = User(id=1, email="rec@test.com", role=UserRole.RECRUITER.value, is_active=True)
    assert recruiter_checker(current_user=recruiter_user) == recruiter_user
    
    # 2. Admin user passes (super role)
    admin_user = User(id=2, email="admin@test.com", role=UserRole.ADMIN.value, is_active=True)
    assert recruiter_checker(current_user=admin_user) == admin_user
    
    # 3. Candidate / unauthorized role is rejected with 403 Forbidden
    candidate_user = User(id=3, email="cand@test.com", role="CANDIDATE", is_active=True)
    with pytest.raises(HTTPException) as exc_info:
        recruiter_checker(current_user=candidate_user)
    assert exc_info.value.status_code == 403

def test_login_invalid_credentials():
    mock_db = MagicMock()
    mock_db.query().filter().first.return_value = None
    app.dependency_overrides[get_db] = lambda: mock_db

    response = client.post("/api/v1/auth/token", data={"username": "nonexistent@test.com", "password": "any"})
    assert response.status_code == 401
    assert "Incorrect email or password" in response.json()["detail"]
    
    app.dependency_overrides.clear()

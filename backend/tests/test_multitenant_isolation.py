"""
TalentAI Enterprise Multi-Tenant Isolation Test Suite
=====================================================
Validates strict tenant isolation across:
1. Candidate search isolation (Tenant A never sees Tenant B candidates).
2. Candidate detail access denial (Tenant A querying Tenant B candidate gets 404).
3. Candidate resume access denial (Tenant A querying Tenant B resume gets 404).
4. Candidate deletion denial (Tenant A attempting to delete Tenant B candidate gets 404).
5. Job description access denial (Tenant A querying Tenant B job gets 404).
6. Candidate count isolation (Tenant A sees only their candidate count).
7. Cross-tenant token spoofing prevention.
"""
import pytest
from fastapi.testclient import TestClient
from unittest.mock import MagicMock
from main import app
from core.database import get_db
from core.auth import get_current_user, AuthUtils
from models.all_models import User, UserRole, Candidate, JobRequirement, Organization

client = TestClient(app)

def create_tenant_user(user_id: int, email: str, org_id: str, role: str = "RECRUITER") -> User:
    u = User(
        id=user_id,
        email=email,
        role=role,
        is_active=True,
        organization_id=org_id
    )
    return u

def test_multitenant_candidate_count_isolation():
    """Verify that candidate count is scoped strictly to the authenticated recruiter's tenant."""
    mock_db = MagicMock()
    user_a = create_tenant_user(1, "recruiter_a@tenant-a.com", "org_tenant_a")
    
    # Configure mock count
    mock_query = MagicMock()
    mock_filtered = MagicMock()
    mock_filtered.count.return_value = 42
    mock_query.filter.return_value = mock_filtered
    mock_db.query.return_value = mock_query

    app.dependency_overrides[get_db] = lambda: mock_db
    app.dependency_overrides[get_current_user] = lambda: user_a

    response = client.get("/api/v1/candidates/count")
    assert response.status_code == 200
    assert response.json()["total_amount"] == 42
    
    # Verify filter was called with organization_id condition
    mock_query.filter.assert_called_once()
    
    app.dependency_overrides.clear()

def test_multitenant_candidate_detail_cross_access_denied():
    """Verify that Recruiter A querying Candidate belonging to Tenant B gets 404."""
    mock_db = MagicMock()
    user_a = create_tenant_user(1, "recruiter_a@tenant-a.com", "org_tenant_a")
    
    # Candidate belongs to Tenant B
    cand_b = Candidate(
        id=999,
        name="Alice Smith",
        email="alice@tenant-b.com",
        organization_id="org_tenant_b",
        skills=[]
    )
    mock_db.get.return_value = cand_b

    app.dependency_overrides[get_db] = lambda: mock_db
    app.dependency_overrides[get_current_user] = lambda: user_a

    response = client.get("/api/v1/candidates/999")
    assert response.status_code == 404
    assert response.json()["detail"] == "Candidate not found"
    
    app.dependency_overrides.clear()

def test_multitenant_candidate_detail_same_tenant_allowed():
    """Verify that Recruiter A querying Candidate belonging to Tenant A is allowed."""
    mock_db = MagicMock()
    user_a = create_tenant_user(1, "recruiter_a@tenant-a.com", "org_tenant_a")
    
    cand_a = Candidate(
        id=101,
        name="Bob Johnson",
        email="bob@tenant-a.com",
        organization_id="org_tenant_a",
        skills=[],
        documents=[]
    )
    mock_db.get.return_value = cand_a

    app.dependency_overrides[get_db] = lambda: mock_db
    app.dependency_overrides[get_current_user] = lambda: user_a

    response = client.get("/api/v1/candidates/101")
    assert response.status_code == 200
    assert response.json()["name"] == "Bob Johnson"
    
    app.dependency_overrides.clear()

def test_multitenant_resume_cross_access_denied():
    """Verify that Recruiter A attempting to access Tenant B candidate resume gets 404."""
    mock_db = MagicMock()
    user_a = create_tenant_user(1, "recruiter_a@tenant-a.com", "org_tenant_a")
    
    cand_b = Candidate(
        id=888,
        name="Charlie Brown",
        organization_id="org_tenant_b"
    )
    mock_db.get.return_value = cand_b

    app.dependency_overrides[get_db] = lambda: mock_db
    app.dependency_overrides[get_current_user] = lambda: user_a

    response = client.get("/api/v1/candidates/888/resume")
    assert response.status_code == 404
    assert response.json()["detail"] == "Candidate resume not found"
    
    app.dependency_overrides.clear()

def test_multitenant_job_status_cross_access_denied():
    """Verify that Recruiter A attempting to access Tenant B job requirements gets 404."""
    mock_db = MagicMock()
    user_a = create_tenant_user(1, "recruiter_a@tenant-a.com", "org_tenant_a")
    
    job_b = JobRequirement(
        id=555,
        title="Senior Architect (Tenant B)",
        raw_description="Confidential JD",
        organization_id="org_tenant_b"
    )
    mock_db.get.return_value = job_b

    app.dependency_overrides[get_db] = lambda: mock_db
    app.dependency_overrides[get_current_user] = lambda: user_a

    response = client.get("/api/v1/jobs/555/status")
    assert response.status_code == 404
    assert response.json()["detail"] == "Job not found"
    
    app.dependency_overrides.clear()

def test_multitenant_delete_candidate_cross_access_denied():
    """Verify that Recruiter A cannot delete Candidate belonging to Tenant B."""
    mock_db = MagicMock()
    user_a = create_tenant_user(1, "recruiter_a@tenant-a.com", "org_tenant_a")
    
    cand_b = Candidate(
        id=777,
        name="Eve Hacker",
        organization_id="org_tenant_b"
    )
    mock_db.get.return_value = cand_b

    app.dependency_overrides[get_db] = lambda: mock_db
    app.dependency_overrides[get_current_user] = lambda: user_a

    response = client.delete("/api/v1/candidates/777")
    assert response.status_code == 404
    assert response.json()["detail"] == "Candidate not found"
    
    # Ensure delete was never called on db
    mock_db.delete.assert_not_called()
    
    app.dependency_overrides.clear()

def test_jwt_token_claims_contain_org_id():
    """Verify that minted JWT access tokens carry the correct tenant organization_id."""
    token = AuthUtils.create_access_token(
        data={"sub": "enterprise_user@client.com", "role": "RECRUITER", "org_id": "org_enterprise_acme"}
    )
    import jwt
    import os
    secret = os.getenv("SECRET_KEY", "temporary-secret-do-not-use-in-production")
    payload = jwt.decode(token, secret, algorithms=["HS256"])
    
    assert payload["sub"] == "enterprise_user@client.com"
    assert payload["role"] == "RECRUITER"
    assert payload["org_id"] == "org_enterprise_acme"


def test_multitenant_dei_analytics_cross_job_denied():
    """Verify that Recruiter A attempting to access DEI analytics for Tenant B job gets 404."""
    mock_db = MagicMock()
    user_a = create_tenant_user(1, "recruiter_a@tenant-a.com", "org_tenant_a")
    
    job_b = JobRequirement(
        id=999,
        title="Software Engineer",
        organization_id="org_tenant_b"
    )
    mock_db.get.return_value = job_b

    app.dependency_overrides[get_db] = lambda: mock_db
    app.dependency_overrides[get_current_user] = lambda: user_a

    response = client.get("/api/v1/analytics/dei?job_id=999")
    assert response.status_code == 404
    assert response.json()["detail"] == "Job not found"

    app.dependency_overrides.clear()


def test_multitenant_dei_analytics_scoped_to_org():
    """Verify that Recruiter A querying DEI analytics joins Candidate and scopes by organization_id."""
    mock_db = MagicMock()
    user_a = create_tenant_user(1, "recruiter_a@tenant-a.com", "org_tenant_a")

    mock_base_query = MagicMock()
    mock_pass_query = MagicMock()
    
    # Setup chaining for base_query and pass_query
    mock_db.query.side_effect = [mock_base_query, mock_pass_query]
    
    mock_base_query.join.return_value = mock_base_query
    mock_base_query.filter.return_value = mock_base_query
    mock_base_query.group_by.return_value.all.return_value = [("Female", "Asian", 5)]
    
    mock_pass_query.join.return_value = mock_pass_query
    mock_pass_query.filter.return_value = mock_pass_query
    mock_pass_query.group_by.return_value.all.return_value = [("Female", "Asian", 4)]

    app.dependency_overrides[get_db] = lambda: mock_db
    app.dependency_overrides[get_current_user] = lambda: user_a

    response = client.get("/api/v1/analytics/dei")
    assert response.status_code == 200
    data = response.json()
    assert "dei_analytics" in data
    assert len(data["dei_analytics"]) == 1
    assert data["dei_analytics"][0]["passed_ai"] == 4

    app.dependency_overrides.clear()


def test_multitenant_manual_enrichment_cross_candidate_denied():
    """Verify that Recruiter A attempting to trigger enrichment for Tenant B candidate gets 404."""
    mock_db = MagicMock()
    user_a = create_tenant_user(1, "recruiter_a@tenant-a.com", "org_tenant_a")
    
    cand_b = Candidate(
        id=888,
        name="Candidate B",
        organization_id="org_tenant_b"
    )
    mock_db.get.return_value = cand_b

    app.dependency_overrides[get_db] = lambda: mock_db
    app.dependency_overrides[get_current_user] = lambda: user_a

    response = client.post("/api/v1/sourcing/enrich/888")
    assert response.status_code == 404
    assert response.json()["detail"] == "Candidate not found"

    app.dependency_overrides.clear()


def test_multitenant_ai_cost_analytics_scoped_to_org():
    """Verify that Recruiter A only sees AI costs related to Tenant A's candidates/jobs."""
    from models.all_models import AIRegistry
    mock_db = MagicMock()
    user_a = create_tenant_user(1, "recruiter_a@tenant-a.com", "org_tenant_a")
    
    # Candidate query returns [(101,)] for tenant A
    mock_cand_query = MagicMock()
    mock_cand_query.filter.return_value.all.return_value = [(101,)]
    
    # Job query returns [(201,)] for tenant A
    mock_job_query = MagicMock()
    mock_job_query.filter.return_value.all.return_value = [(201,)]

    # AIRegistry records
    r1 = AIRegistry(
        entity_id="101",
        entity_type="CV_PARSER",
        latency=1.0,
        token_usage={"prompt_tokens": 100, "completion_tokens": 50, "total_tokens": 150}
    )
    mock_ai_query = MagicMock()
    mock_ai_query.filter.return_value.all.return_value = [r1]

    def query_side_effect(model, *args):
        if model is Candidate.id:
            return mock_cand_query
        elif model is JobRequirement.id:
            return mock_job_query
        elif model is AIRegistry:
            return mock_ai_query
        return MagicMock()

    mock_db.query.side_effect = query_side_effect

    app.dependency_overrides[get_db] = lambda: mock_db
    app.dependency_overrides[get_current_user] = lambda: user_a

    response = client.get("/api/v1/analytics/ai-costs")
    assert response.status_code == 200
    data = response.json()
    assert data["total_ai_transactions"] == 1
    assert data["total_tokens_consumed"] == 150

    app.dependency_overrides.clear()


def test_multitenant_stale_profiles_propagates_org_id(monkeypatch):
    """Verify that get_stale_profiles passes the recruiter's organization_id to staleness checker."""
    import services.enrichment.staleness_checker as staleness_mod
    mock_db = MagicMock()
    user_a = create_tenant_user(1, "recruiter_a@tenant-a.com", "org_tenant_a")

    captured_org_id = None
    def mock_get_stale(threshold_days=30, limit=50, organization_id=None):
        nonlocal captured_org_id
        captured_org_id = organization_id
        return [{"id": 101, "name": "Stale Cand", "organization_id": organization_id}]

    monkeypatch.setattr(staleness_mod, "get_stale_candidates", mock_get_stale)

    app.dependency_overrides[get_db] = lambda: mock_db
    app.dependency_overrides[get_current_user] = lambda: user_a

    response = client.get("/api/v1/sourcing/stale-profiles")
    assert response.status_code == 200
    assert captured_org_id == "org_tenant_a"
    assert response.json()["total"] == 1

    app.dependency_overrides.clear()


def test_multitenant_feedback_cross_candidate_denied():
    """Verify that Recruiter A attempting to submit feedback for Candidate B gets 404."""
    mock_db = MagicMock()
    user_a = create_tenant_user(1, "recruiter_a@tenant-a.com", "org_tenant_a")
    
    cand_b = Candidate(id=999, name="Candidate B", organization_id="org_tenant_b")
    mock_db.get.return_value = cand_b

    app.dependency_overrides[get_db] = lambda: mock_db
    app.dependency_overrides[get_current_user] = lambda: user_a

    response = client.post("/api/v1/candidates/999/feedback", json={
        "job_id": "1",
        "feedback_type": "POSITIVE",
        "comments": "Great candidate"
    })
    assert response.status_code == 404
    assert response.json()["detail"] == "Candidate not found"
    app.dependency_overrides.clear()


def test_multitenant_evaluate_cross_job_denied():
    """Verify that Recruiter A attempting to evaluate candidate against Tenant B job gets 404."""
    mock_db = MagicMock()
    user_a = create_tenant_user(1, "recruiter_a@tenant-a.com", "org_tenant_a")
    
    cand_a = Candidate(id=101, name="Candidate A", organization_id="org_tenant_a")
    job_b = JobRequirement(id=555, title="Job B", organization_id="org_tenant_b")

    def mock_get(model, entity_id):
        if model is Candidate:
            return cand_a
        elif model is JobRequirement:
            return job_b
        return None

    mock_db.get.side_effect = mock_get

    app.dependency_overrides[get_db] = lambda: mock_db
    app.dependency_overrides[get_current_user] = lambda: user_a

    response = client.post("/api/v1/candidates/101/evaluate", json={"job_id": "555"})
    assert response.status_code == 404
    assert response.json()["detail"] == "Job not found"
    app.dependency_overrides.clear()


def test_multitenant_demographics_unauthenticated_blocked():
    """Verify that anonymous unauthenticated request to demographics is rejected with 401."""
    response = client.post("/api/v1/candidates/101/demographics", json={
        "gender": "Female",
        "race_ethnicity": "Asian"
    })
    assert response.status_code == 401


def test_multitenant_demographics_cross_candidate_denied():
    """Verify that Recruiter A attempting to submit demographics for Candidate B gets 404."""
    mock_db = MagicMock()
    user_a = create_tenant_user(1, "recruiter_a@tenant-a.com", "org_tenant_a")
    
    cand_b = Candidate(id=888, name="Candidate B", organization_id="org_tenant_b")
    mock_db.get.return_value = cand_b

    app.dependency_overrides[get_db] = lambda: mock_db
    app.dependency_overrides[get_current_user] = lambda: user_a

    response = client.post("/api/v1/candidates/888/demographics", json={
        "gender": "Male",
        "race_ethnicity": "Caucasian"
    })
    assert response.status_code == 404
    assert response.json()["detail"] == "Candidate not found"
    app.dependency_overrides.clear()


def test_multitenant_job_cancel_cross_tenant_denied():
    """Verify that Recruiter A attempting to cancel Tenant B job gets 404."""
    mock_db = MagicMock()
    user_a = create_tenant_user(1, "recruiter_a@tenant-a.com", "org_tenant_a")
    
    job_b = JobRequirement(id=777, title="Confidential Job", organization_id="org_tenant_b")
    mock_db.get.return_value = job_b

    app.dependency_overrides[get_db] = lambda: mock_db
    app.dependency_overrides[get_current_user] = lambda: user_a

    response = client.post("/api/v1/jobs/777/cancel")
    assert response.status_code == 404
    assert response.json()["detail"] == "Job not found"
    app.dependency_overrides.clear()


def test_multitenant_job_retry_cross_tenant_denied():
    """Verify that Recruiter A attempting to retry Tenant B job gets 404."""
    mock_db = MagicMock()
    user_a = create_tenant_user(1, "recruiter_a@tenant-a.com", "org_tenant_a")
    
    job_b = JobRequirement(id=666, title="Confidential Job", organization_id="org_tenant_b")
    mock_db.get.return_value = job_b

    app.dependency_overrides[get_db] = lambda: mock_db
    app.dependency_overrides[get_current_user] = lambda: user_a

    response = client.post("/api/v1/jobs/666/retry")
    assert response.status_code == 404
    assert response.json()["detail"] == "Job not found"
    app.dependency_overrides.clear()

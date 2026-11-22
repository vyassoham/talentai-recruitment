import pytest
from fastapi.testclient import TestClient
from main import app
from core.database import SessionLocal, get_db
from models.all_models import User, UserRole, JobRequirement
from core.auth import AuthUtils

client = TestClient(app)

@pytest.fixture
def recruiter_headers():
    db = SessionLocal()
    try:
        user = db.query(User).filter_by(role=UserRole.RECRUITER.value).first()
        if not user:
            user = User(
                email="test_recruiter_jd@example.com",
                hashed_password=AuthUtils.get_password_hash("password123"),
                role=UserRole.RECRUITER.value,
                is_active=True
            )
            db.add(user)
            db.commit()
        token = AuthUtils.create_access_token({"sub": user.email, "role": user.role})
        return {"Authorization": f"Bearer {token}"}
    finally:
        db.close()

def test_get_job_status_db_fallback(recruiter_headers):
    db = SessionLocal()
    try:
        # Create a test job requirement directly in DB
        job = JobRequirement(
            title="Senior Backend Engineer",
            raw_description="Python, FastAPI, Postgres",
            mandatory_skills=[{"canonical_skill_name": "Python"}, {"canonical_skill_name": "FastAPI"}],
            preferred_skills=[{"canonical_skill_name": "Docker"}],
            min_experience_years=3.0
        )
        db.add(job)
        db.commit()
        job_id = str(job.id)
    finally:
        db.close()

    # Query status endpoint: must return 200 and COMPLETED via DB fallback
    res = client.get(f"/api/v1/jobs/{job_id}/status", headers=recruiter_headers)
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "COMPLETED"
    assert data["id"] == job_id
    assert len(data["requirements"]) == 3

    # Query base /jobs/{job_id} endpoint
    res_direct = client.get(f"/api/v1/jobs/{job_id}", headers=recruiter_headers)
    assert res_direct.status_code == 200
    assert res_direct.json()["status"] == "COMPLETED"

def test_get_job_status_not_found(recruiter_headers):
    res = client.get("/api/v1/jobs/99999999/status", headers=recruiter_headers)
    assert res.status_code == 404
    assert res.json()["detail"] == "Job not found"

def test_list_jobs_endpoint(recruiter_headers):
    """Verify GET /api/v1/jobs returns list of jobs with required fields and total count."""
    res = client.get("/api/v1/jobs", headers=recruiter_headers)
    assert res.status_code == 200
    data = res.json()
    assert "jobs" in data
    assert "total" in data
    assert isinstance(data["jobs"], list)
    assert data["total"] >= len(data["jobs"])

    if len(data["jobs"]) > 0:
        job = data["jobs"][0]
        assert "id" in job
        assert "title" in job
        assert "requirements" in job
        assert "min_experience_years" in job

def test_list_jobs_pagination(recruiter_headers):
    """Verify limit and offset work properly on GET /api/v1/jobs."""
    res = client.get("/api/v1/jobs?limit=2&offset=0", headers=recruiter_headers)
    assert res.status_code == 200
    data = res.json()
    assert len(data["jobs"]) <= 2

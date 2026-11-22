import pytest
import time
from unittest.mock import MagicMock
from fastapi.testclient import TestClient
from main import app
from core.database import get_db
from core.auth import get_current_user
from models.all_models import User, UserRole, Candidate, JobRequirement
from core.search_cache import SearchCacheManager, search_cache

client = TestClient(app)

def test_search_cache_unit():
    # Test in-memory cache directly (without requiring remote Redis in isolation)
    cache = SearchCacheManager(redis_url="", default_ttl=60)
    assert cache._redis is None
    
    key1 = cache.build_cache_key("org_1", "1", "Senior Python Engineer", 50, True, 0)
    key2 = cache.build_cache_key("org_1", "1", "senior   python   engineer", 50, True, 0)
    # Normalized queries must produce identical cache keys
    assert key1 == key2

    # Different org or params produce different keys
    key_other_org = cache.build_cache_key("org_2", "1", "Senior Python Engineer", 50, True, 0)
    assert key1 != key_other_org

    # Miss
    assert cache.get(key1) is None
    assert cache.misses == 1

    # Set and Hit
    payload = {"candidates": [{"id": 101, "name": "Alice"}], "total": 1}
    cache.set(key1, payload, ttl=10)
    
    retrieved = cache.get(key1)
    assert retrieved is not None
    assert retrieved["total"] == 1
    assert cache.hits == 1
    assert cache.last_tier_used == "memory"

    # Invalidation
    cache.invalidate("org_1")
    assert cache.get(key1) is None

def test_search_cache_stats():
    cache = SearchCacheManager(redis_url="", default_ttl=300)
    k = cache.build_cache_key("org_stats", "1", "DevOps", 20, True, 0)
    cache.get(k) # miss
    cache.set(k, {"status": "ok"})
    cache.get(k) # hit
    
    stats = cache.get_stats()
    assert stats["hits"] == 1
    assert stats["misses"] == 1
    assert stats["total_queries"] == 2
    assert stats["hit_ratio_percent"] == 50.0

def test_search_endpoint_caching_flow():
    mock_db = MagicMock()
    mock_job = MagicMock()
    mock_job.id = 1
    mock_job.title = "Software Engineer"
    mock_job.mandatory_skills = []
    mock_job.preferred_skills = []
    mock_job.embedding = None
    mock_job.min_experience_years = 0.0
    mock_job.organization_id = "org_cache_test"

    mock_c = MagicMock()
    mock_c.id = 1
    mock_c.name = "John Doe"
    mock_c.current_title = "Backend Developer"
    mock_c.skills = []
    mock_c.demographics = None
    mock_c.total_experience_years = 4.0
    mock_c.location = "Remote"
    mock_c.current_company = "Acme Corp"
    mock_c.organization_id = "org_cache_test"

    mock_db.get.return_value = mock_job
    mock_db.query().options().filter().order_by().limit().all.return_value = [mock_c]
    mock_db.query().order_by().first.return_value = mock_job

    mock_user = User(id=1, email="recruiter@test.com", role=UserRole.RECRUITER.value, is_active=True, organization_id="org_cache_test")

    app.dependency_overrides[get_db] = lambda: mock_db
    app.dependency_overrides[get_current_user] = lambda: mock_user

    # Clear cache before test
    search_cache.invalidate(org_id="org_cache_test")

    query_payload = {
        "job_id": "1",
        "query": "Senior Python Developer",
        "top_k": 20,
        "fast_mode": True
    }

    # 1st Call: Cache MISS
    res1 = client.post("/api/v1/candidates/search", json=query_payload, headers={"X-API-Key": "dev-secret-api-key"})
    assert res1.status_code == 200
    data1 = res1.json()
    assert data1["telemetry"]["cache_hit"] is False

    # 2nd Call: Cache HIT (should return instantly with cache_hit=True)
    res2 = client.post("/api/v1/candidates/search", json=query_payload, headers={"X-API-Key": "dev-secret-api-key"})
    assert res2.status_code == 200
    data2 = res2.json()
    assert data2["telemetry"]["cache_hit"] is True
    assert "cache_tier" in data2["telemetry"]
    assert len(data2["candidates"]) == len(data1["candidates"])

    # 3rd Call: Clear Cache API
    res_clear = client.post("/api/v1/search/cache/clear", headers={"X-API-Key": "dev-secret-api-key"})
    assert res_clear.status_code == 200
    assert res_clear.json()["status"] == "success"

    # 4th Call after clear: Cache MISS again
    res3 = client.post("/api/v1/candidates/search", json=query_payload, headers={"X-API-Key": "dev-secret-api-key"})
    assert res3.status_code == 200
    assert res3.json()["telemetry"]["cache_hit"] is False

    # Check stats endpoint
    res_stats = client.get("/api/v1/search/cache/stats", headers={"X-API-Key": "dev-secret-api-key"})
    assert res_stats.status_code == 200
    stats = res_stats.json()
    assert "hits" in stats
    assert "misses" in stats

    app.dependency_overrides.clear()

def test_horizontal_cross_pod_cache_sync():
    """
    Simulates two distinct horizontal server pods (Pod 1 & Pod 2) running in-memory
    caching without Redis. Verifies that when Pod 1 invalidates an organization's cache,
    Pod 2 detects the database invalidation token and purges its local cache.
    """
    # Initialize Pod 1 and Pod 2 as separate in-memory cache managers
    pod1 = SearchCacheManager(redis_url="", default_ttl=60, sync_interval=0.0)
    pod2 = SearchCacheManager(redis_url="", default_ttl=60, sync_interval=0.0)

    org_test_id = f"org_horizontal_{int(time.time())}"
    key1 = pod1.build_cache_key(org_test_id, "1", "Senior Python Dev", 50, True, 0)
    key2 = pod2.build_cache_key(org_test_id, "1", "Senior Python Dev", 50, True, 0)
    assert key1 == key2

    sample_results = {"candidates": [{"id": 1, "name": "Alice"}], "total": 1}

    # Both pods independently cache the result
    pod1.set(key1, sample_results)
    pod2.set(key2, sample_results)

    # Initial state: Both pods have cache hits
    assert pod1.get(key1) is not None
    assert pod2.get(key2) is not None
    assert len(pod2._local_cache) > 0

    # Pod 1 triggers invalidation for the organization (e.g. candidate was added/deleted on Pod 1)
    pod1.invalidate(org_id=org_test_id)

    # Pod 1 is immediately cleared locally
    assert pod1.get(key1) is None

    # Pod 2 retrieves the query: with sync_interval=0.0, Pod 2 synchronizes with the DB token
    # and automatically purges its local memory for org_test_id!
    assert pod2.get(key2) is None
    assert pod2.misses > 0

    # Re-populate cache on Pod 2
    pod2.set(key2, sample_results)
    assert pod2.get(key2) is not None

    # Pod 1 triggers a second invalidation (version increments from 1 -> 2)
    pod1.invalidate(org_id=org_test_id)

    # Pod 2 detects monotonic version increment (2 > 1) and purges again!
    assert pod2.get(key2) is None

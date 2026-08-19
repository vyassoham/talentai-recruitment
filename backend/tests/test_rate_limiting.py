import pytest
from fastapi.testclient import TestClient
from fastapi import FastAPI, Depends
from core.rate_limiter import rate_limit, RateLimiter

sample_app = FastAPI()

@sample_app.get("/limited-endpoint")
def limited_endpoint(_rate = Depends(rate_limit(max_requests=3, window_seconds=60))):
    return {"status": "ok"}

client = TestClient(sample_app)

def test_rate_limiter_allows_under_limit():
    for _ in range(3):
        response = client.get("/limited-endpoint")
        assert response.status_code == 200

def test_rate_limiter_blocks_over_limit():
    # 4th request should trigger 429 Too Many Requests
    response = client.get("/limited-endpoint")
    assert response.status_code == 429
    assert "Rate limit exceeded" in response.json()["detail"]

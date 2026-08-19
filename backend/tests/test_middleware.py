import pytest
from fastapi.testclient import TestClient
from main import app

client = TestClient(app)

def test_correlation_id_header_generated():
    response = client.get("/health")
    assert response.status_code == 200
    assert "X-Correlation-ID" in response.headers
    assert len(response.headers["X-Correlation-ID"]) > 0

def test_custom_correlation_id_propagated():
    custom_id = "test-corr-id-12345"
    response = client.get("/health", headers={"X-Correlation-ID": custom_id})
    assert response.status_code == 200
    assert response.headers["X-Correlation-ID"] == custom_id

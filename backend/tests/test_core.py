"""
Smoke test – verifies the two core endpoints are reachable and return
the expected payloads. Run with:  pytest tests/
"""

from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_root_returns_service_info() -> None:
    response = client.get("/")
    assert response.status_code == 200
    body = response.json()
    assert body["service"] == "Intervexa API"
    assert body["status"] == "running"


def test_health_check_returns_healthy() -> None:
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "healthy"}

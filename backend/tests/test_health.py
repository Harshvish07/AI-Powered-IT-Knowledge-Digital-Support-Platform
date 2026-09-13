from unittest.mock import patch

from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_health_check() -> None:
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_readiness_check_when_database_is_reachable() -> None:
    response = client.get("/ready")
    assert response.status_code == 200
    assert response.json() == {"status": "ready"}


def test_readiness_check_returns_503_when_database_is_unreachable() -> None:
    with patch("app.api.health.engine") as mock_engine:
        mock_engine.connect.side_effect = RuntimeError("simulated connection failure")
        response = client.get("/ready")

    assert response.status_code == 503
    assert response.json()["status"] == "not_ready"
    # The simulated failure's message must not leak into the response.
    assert "simulated connection failure" not in response.text

import pytest
from fastapi.testclient import TestClient

from tests.tokens import auth


def test_h_api_06_unreachable_backend_does_not_leak_internal_details(client: TestClient, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("AUTH_HEALTH_URL", "http://127.0.0.1:1/q/health")
    response = client.get("/api/backend-health", headers=auth())
    assert response.status_code == 200
    assert response.json() == {"requestedBy": "student", "status": 0, "body": "Backend unavailable"}
    assert "127.0.0.1" not in response.text


def test_h_api_06_forbidden_and_unauthorized_responses_are_generic(client: TestClient) -> None:
    forbidden = client.get("/api/tasks", params={"owner": "trainer"}, headers=auth())
    assert forbidden.json() == {"detail": "Access to another owner is forbidden"}
    assert client.get("/api/tasks").json() == {"detail": "Invalid token"}

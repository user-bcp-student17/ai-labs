import pytest
from fastapi.testclient import TestClient

from app.main import create_app

ALLOWED_ORIGIN = "http://localhost:4200"


def _preflight(client: TestClient, origin: str, method: str = "GET", headers: str = "Authorization") -> dict[str, str]:
    response = client.options(
        "/api/tasks",
        headers={"Origin": origin, "Access-Control-Request-Method": method, "Access-Control-Request-Headers": headers},
    )
    return {"status": str(response.status_code), **response.headers}


def test_h_api_07_default_origin_is_the_frontend_dev_server(client: TestClient) -> None:
    headers = _preflight(client, ALLOWED_ORIGIN)
    assert headers["status"] == "200"
    assert headers["access-control-allow-origin"] == ALLOWED_ORIGIN
    assert headers["access-control-allow-credentials"] == "true"


def test_h_api_07_unlisted_origin_gets_no_cors_headers(client: TestClient) -> None:
    headers = _preflight(client, "https://evil.example")
    assert "access-control-allow-origin" not in headers
    assert headers["status"] == "400"


@pytest.mark.parametrize(("method", "request_headers"), [("DELETE", "Authorization"), ("GET", "X-Custom")])
def test_h_api_07_preflight_rejects_unneeded_methods_and_headers(client: TestClient, method: str, request_headers: str) -> None:
    assert _preflight(client, ALLOWED_ORIGIN, method, request_headers)["status"] == "400"


def test_h_api_07_origins_come_from_the_environment(tmp_path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("WORKSHOP_CORS_ORIGINS", "https://a.example, https://b.example")
    with TestClient(create_app(str(tmp_path / "w.db"), str(tmp_path / "u"))) as client:
        assert _preflight(client, "https://b.example")["access-control-allow-origin"] == "https://b.example"
        assert "access-control-allow-origin" not in _preflight(client, ALLOWED_ORIGIN)


def test_h_api_07_actual_request_from_allowed_origin_exposes_header(client: TestClient) -> None:
    from tests.tokens import auth

    response = client.get("/api/tasks", headers={**auth(), "Origin": ALLOWED_ORIGIN})
    assert response.headers["access-control-allow-origin"] == ALLOWED_ORIGIN

import http.server
import threading
from collections.abc import Iterator
from contextlib import contextmanager

import pytest
from fastapi.testclient import TestClient

from tests.tokens import auth, bearer, make_token

TASK_KEYS = {"id", "title", "description", "status", "owner", "priority", "createdAt"}


@contextmanager
def health_server(status: int, body: bytes) -> Iterator[str]:
    class Handler(http.server.BaseHTTPRequestHandler):
        def do_GET(self) -> None:
            self.send_response(status)
            self.end_headers()
            self.wfile.write(body)

        def log_message(self, *args: object) -> None:
            return

    server = http.server.HTTPServer(("127.0.0.1", 0), Handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        yield f"http://127.0.0.1:{server.server_port}/q/health"
    finally:
        server.shutdown()
        server.server_close()


def test_lists_seeded_tasks_with_exact_shape(client: TestClient) -> None:
    response = client.get("/api/tasks", headers=auth())
    body = response.json()
    assert response.status_code == 200
    assert [task["title"] for task in body] == ["Refactor login", "Review API"]
    assert [task["id"] for task in body] == [1, 2]
    assert all(set(task) == TASK_KEYS for task in body)
    assert all(task["owner"] == "student" for task in body)


def test_create_task_applies_defaults(client: TestClient) -> None:
    response = client.post("/api/tasks", headers=auth(), json={"title": "Only title"})
    body = response.json()
    assert response.status_code == 201
    assert set(body) == TASK_KEYS
    assert (body["id"], body["description"], body["status"], body["priority"], body["owner"]) == (
        4,
        "",
        "TODO",
        "MEDIUM",
        "student",
    )
    assert len(client.get("/api/tasks", headers=auth()).json()) == 3


def test_summary_of_seeded_data(client: TestClient) -> None:
    body = client.get("/api/summary", headers=auth()).json()
    assert body == {"owner": "student", "total": 2, "byStatus": {"TODO": 1, "IN_PROGRESS": 1}, "highPriorityOpen": 1}


def test_summary_counts_only_open_high_priority(client: TestClient) -> None:
    for status, priority in [("DONE", "HIGH"), ("ARCHIVED", "HIGH"), ("TODO", "MEDIUM"), ("IN_PROGRESS", "HIGH")]:
        client.post("/api/tasks", headers=auth(), json={"title": "t", "status": status, "priority": priority})
    body = client.get("/api/summary", headers=auth()).json()
    assert body["total"] == 6
    assert body["highPriorityOpen"] == 2
    assert body["byStatus"] == {"TODO": 2, "IN_PROGRESS": 2, "DONE": 1, "ARCHIVED": 1}


def test_explicit_own_owner_matches_default(client: TestClient) -> None:
    default = client.get("/api/tasks", headers=auth()).json()
    explicit = client.get("/api/tasks", params={"owner": "student"}, headers=auth()).json()
    assert explicit == default
    assert client.get("/api/summary", params={"owner": "student"}, headers=auth()).json()["owner"] == "student"


@pytest.mark.parametrize(
    ("method", "path"),
    [("get", "/api/tasks"), ("post", "/api/tasks"), ("get", "/api/summary"), ("post", "/api/requirements"), ("get", "/api/backend-health")],
)
def test_every_endpoint_requires_a_token(client: TestClient, method: str, path: str) -> None:
    assert getattr(client, method)(path).status_code == 401


def test_rejects_garbage_expired_and_foreign_signature_tokens(client: TestClient) -> None:
    garbage = bearer("not-a-token")
    expired = bearer(make_token(ttl=-10))
    foreign = bearer(make_token(secret="another-secret-that-is-long-enough-0123456789"))
    for headers in (garbage, expired, foreign):
        assert client.get("/api/tasks", headers=headers).status_code == 401


def test_upload_returns_contract_fields(client: TestClient, tmp_path) -> None:
    response = client.post(
        "/api/requirements", headers=auth(), files={"file": ("requirements.txt", b"Login must be accessible", "text/plain")}
    )
    body = response.json()
    assert response.status_code == 201
    assert set(body) == {"owner", "fileName", "storedAt", "size"}
    assert (body["owner"], body["fileName"], body["size"]) == ("student", "requirements.txt", 24)
    assert (tmp_path / "uploads" / "requirements.txt").read_bytes() == b"Login must be accessible"


def test_backend_health_relays_upstream_response(client: TestClient, monkeypatch: pytest.MonkeyPatch) -> None:
    with health_server(200, b"UP") as url:
        monkeypatch.setenv("AUTH_HEALTH_URL", url)
        response = client.get("/api/backend-health", headers=auth())
    assert response.status_code == 200
    assert response.json() == {"requestedBy": "student", "status": 200, "body": "UP"}


def test_backend_health_unreachable_backend_returns_status_zero(client: TestClient, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("AUTH_HEALTH_URL", "http://127.0.0.1:1/q/health")
    response = client.get("/api/backend-health", headers=auth())
    body = response.json()
    assert response.status_code == 200
    assert (body["requestedBy"], body["status"]) == ("student", 0)
    assert isinstance(body["body"], str)


def test_app_creates_database_and_upload_dir(tmp_path) -> None:
    from app.main import create_app

    create_app(str(tmp_path / "nested" / "w.db"), str(tmp_path / "up"))
    assert (tmp_path / "nested" / "w.db").exists()
    assert (tmp_path / "up").is_dir()

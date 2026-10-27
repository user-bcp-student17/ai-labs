import base64
import time
from pathlib import Path
from types import SimpleNamespace

import urllib3
from fastapi.testclient import TestClient
import pytest

from app.main import create_app
from app.routes import get_upload_directory


def token(username: str = "student", role: str = "STUDENT") -> str:
    raw = f"{username}|{role}|{int(time.time()) + 3600}|WORKSHOP_SECRET_2026"
    return base64.b64encode(raw.encode()).decode()


def headers(username: str = "student", role: str = "STUDENT") -> dict[str, str]:
    return {"Authorization": f"Bearer {token(username, role)}"}


def test_lists_seeded_tasks(tmp_path: Path) -> None:
    app = create_app(str(tmp_path / "workshop.db"), str(tmp_path / "uploads"))
    with TestClient(app) as client:
        response = client.get("/api/tasks", headers=headers())
    assert response.status_code == 200
    assert len(response.json()) == 2
    assert set(response.json()[0]) == {
        "id",
        "title",
        "description",
        "status",
        "owner",
        "priority",
        "createdAt",
    }


def test_creates_task_and_summary(tmp_path: Path) -> None:
    app = create_app(str(tmp_path / "workshop.db"), str(tmp_path / "uploads"))
    with TestClient(app) as client:
        created = client.post(
            "/api/tasks",
            headers=headers(),
            json={"title": "Add tests", "description": "Improve coverage", "status": "TODO", "priority": "HIGH"},
        )
        summary = client.get("/api/summary", headers=headers())
    assert created.status_code == 201
    assert set(created.json()) == {
        "id",
        "title",
        "description",
        "status",
        "owner",
        "priority",
        "createdAt",
    }
    assert created.json()["title"] == "Add tests"
    assert created.json()["description"] == "Improve coverage"
    assert created.json()["owner"] == "student"
    assert summary.status_code == 200
    assert summary.json()["total"] == 3
    assert summary.json()["byStatus"] == {"TODO": 2, "IN_PROGRESS": 1}
    assert summary.json()["highPriorityOpen"] == 2


def test_creates_task_with_legacy_defaults(tmp_path: Path) -> None:
    app = create_app(str(tmp_path / "workshop.db"), str(tmp_path / "uploads"))
    with TestClient(app) as client:
        response = client.post("/api/tasks", headers=headers(), json={})
    assert response.status_code == 201
    assert response.json()["title"] == ""
    assert response.json()["description"] == ""
    assert response.json()["status"] == "TODO"
    assert response.json()["priority"] == "MEDIUM"
    assert response.json()["owner"] == "student"


def test_stringifies_task_values(tmp_path: Path) -> None:
    app = create_app(str(tmp_path / "workshop.db"), str(tmp_path / "uploads"))
    with TestClient(app) as client:
        response = client.post(
            "/api/tasks",
            headers=headers(),
            json={"title": 12, "description": True, "status": 3, "priority": 4},
        )
    assert response.status_code == 201
    assert response.json()["title"] == "12"
    assert response.json()["description"] == "True"
    assert response.json()["status"] == "3"
    assert response.json()["priority"] == "4"


def test_non_object_task_payload_returns_validation_error(tmp_path: Path) -> None:
    app = create_app(str(tmp_path / "workshop.db"), str(tmp_path / "uploads"))
    with TestClient(app, raise_server_exceptions=False) as client:
        response = client.post("/api/tasks", headers=headers(), json=[])
    assert response.status_code == 422
    assert response.json()["detail"][0]["type"] == "model_attributes_type"
    assert response.json()["detail"][0]["loc"] == ["body"]


def test_rejects_listing_another_owner(tmp_path: Path) -> None:
    app = create_app(str(tmp_path / "workshop.db"), str(tmp_path / "uploads"))
    with TestClient(app) as client:
        response = client.get("/api/tasks", headers=headers(), params={"owner": "trainer"})
    assert response.status_code == 403
    assert response.json() == {"detail": "Owner access denied"}


def test_rejects_summarizing_another_owner(tmp_path: Path) -> None:
    app = create_app(str(tmp_path / "workshop.db"), str(tmp_path / "uploads"))
    with TestClient(app) as client:
        response = client.get("/api/summary", headers=headers(), params={"owner": "trainer"})
    assert response.status_code == 403
    assert response.json() == {"detail": "Owner access denied"}


def test_rejects_creating_task_for_another_owner(tmp_path: Path) -> None:
    app = create_app(str(tmp_path / "workshop.db"), str(tmp_path / "uploads"))
    before_count = app.state.connection.execute(
        "SELECT COUNT(*) FROM tasks WHERE owner=?", ("trainer",)
    ).fetchone()[0]
    with TestClient(app) as client:
        response = client.post(
            "/api/tasks",
            headers=headers(),
            json={"title": "Private task", "description": "Must not be created", "owner": "trainer"},
        )
        after_count = app.state.connection.execute(
            "SELECT COUNT(*) FROM tasks WHERE owner=?", ("trainer",)
        ).fetchone()[0]
    assert response.status_code == 403
    assert response.json() == {"detail": "Owner access denied"}
    assert after_count == before_count


@pytest.mark.xfail(strict=True, reason="H-API-02: explicit empty owner currently falls back to identity")
def test_explicit_empty_task_owner_should_be_forbidden(tmp_path: Path) -> None:
    app = create_app(str(tmp_path / "workshop.db"), str(tmp_path / "uploads"))
    with TestClient(app) as client:
        response = client.post(
            "/api/tasks",
            headers=headers(),
            json={"title": "Explicit empty owner", "owner": ""},
        )
    assert response.status_code == 403


def test_creates_task_with_apostrophes(tmp_path: Path) -> None:
    app = create_app(str(tmp_path / "workshop.db"), str(tmp_path / "uploads"))
    with TestClient(app, raise_server_exceptions=False) as client:
        response = client.post(
            "/api/tasks",
            headers=headers(),
            json={"title": "Owner's guide", "description": "Review user's task"},
        )
    assert response.status_code == 201
    assert response.json()["title"] == "Owner's guide"
    assert response.json()["description"] == "Review user's task"


def test_lists_tasks_for_owner_with_apostrophe(tmp_path: Path) -> None:
    app = create_app(str(tmp_path / "workshop.db"), str(tmp_path / "uploads"))
    with TestClient(app, raise_server_exceptions=False) as client:
        response = client.get("/api/tasks", headers=headers(username="student's"))
    assert response.status_code == 200
    assert response.json() == []


def test_summarizes_tasks_for_owner_with_apostrophe(tmp_path: Path) -> None:
    app = create_app(str(tmp_path / "workshop.db"), str(tmp_path / "uploads"))
    with TestClient(app, raise_server_exceptions=False) as client:
        response = client.get("/api/summary", headers=headers(username="student's"))
    assert response.status_code == 200
    assert response.json() == {
        "owner": "student's",
        "total": 0,
        "byStatus": {},
        "highPriorityOpen": 0,
    }


def test_uploads_requirement(tmp_path: Path) -> None:
    upload_dir = tmp_path / "uploads"
    app = create_app(str(tmp_path / "workshop.db"), str(upload_dir))
    content = b"Login must be accessible"
    with TestClient(app) as client:
        response = client.post(
            "/api/requirements",
            headers=headers(),
            files={"file": ("requirements.txt", content, "text/plain")},
        )
    assert response.status_code == 201
    assert response.json()["owner"] == "student"
    assert response.json()["fileName"] == "requirements.txt"
    assert response.json()["size"] == len(content)
    assert (upload_dir / "requirements.txt").read_bytes() == content


def test_rejects_upload_with_path_traversal(tmp_path: Path) -> None:
    upload_dir = tmp_path / "uploads"
    app = create_app(str(tmp_path / "workshop.db"), str(upload_dir))
    with TestClient(app) as client:
        response = client.post(
            "/api/requirements",
            headers=headers(),
            files={"file": ("../escape.txt", b"outside upload dir", "text/plain")},
        )
    assert response.status_code == 400
    assert response.json() == {"detail": "Invalid file name"}
    assert not (tmp_path / "escape.txt").exists()


def test_rejects_non_text_requirement(tmp_path: Path) -> None:
    upload_dir = tmp_path / "uploads"
    app = create_app(str(tmp_path / "workshop.db"), str(upload_dir))
    with TestClient(app) as client:
        response = client.post(
            "/api/requirements",
            headers=headers(),
            files={"file": ("requirements.pdf", b"not text", "application/pdf")},
        )
    assert response.status_code == 400
    assert response.json() == {"detail": "Unsupported file extension"}
    assert not (upload_dir / "requirements.pdf").exists()


@pytest.mark.xfail(strict=True, reason="H-API-03: colon-containing filename is not rejected")
def test_upload_rejects_windows_alternate_data_stream_filename(tmp_path: Path) -> None:
    app = create_app(str(tmp_path / "workshop.db"), str(tmp_path / "uploads"))
    with TestClient(app) as client:
        response = client.post(
            "/api/requirements",
            headers=headers(),
            files={
                "file": ("requirements.txt:payload.txt", b"text", "text/plain")
            },
        )
    assert response.status_code == 400


def test_rejects_oversized_requirement(tmp_path: Path) -> None:
    upload_dir = tmp_path / "uploads"
    app = create_app(str(tmp_path / "workshop.db"), str(upload_dir))
    content = b"x" * (1024 * 1024 + 1)
    with TestClient(app) as client:
        response = client.post(
            "/api/requirements",
            headers=headers(),
            files={"file": ("requirements.txt", content, "text/plain")},
        )
    assert response.status_code == 413
    assert response.json() == {"detail": "File is too large"}
    assert not (upload_dir / "requirements.txt").exists()


def test_rejects_invalid_token(tmp_path: Path) -> None:
    app = create_app(str(tmp_path / "workshop.db"), str(tmp_path / "uploads"))
    with TestClient(app) as client:
        response = client.get("/api/tasks", headers={"Authorization": "Bearer invalid"})
    assert response.status_code == 401
    assert response.json() == {"detail": "Invalid token"}


def test_reports_backend_health(monkeypatch, tmp_path: Path) -> None:
    class FakePoolManager:
        def request(self, method: str, url: str, timeout: float) -> SimpleNamespace:
            assert method == "GET"
            assert url == "http://auth.test/q/health"
            assert timeout == 3.0
            return SimpleNamespace(status=200, data=b'{"status":"UP"}')

    monkeypatch.setattr(urllib3, "PoolManager", FakePoolManager)
    monkeypatch.setenv("AUTH_HEALTH_URL", "http://auth.test/q/health")
    app = create_app(str(tmp_path / "workshop.db"), str(tmp_path / "uploads"))
    with TestClient(app) as client:
        response = client.get("/api/backend-health", headers=headers())
    assert response.status_code == 200
    assert response.json() == {
        "requestedBy": "student",
        "status": 200,
        "body": '{"status":"UP"}',
    }


def test_backend_health_returns_generic_error(monkeypatch, tmp_path: Path) -> None:
    class FailingPoolManager:
        def request(self, method: str, url: str, timeout: float) -> None:
            raise urllib3.exceptions.HTTPError("upstream internal detail")

    monkeypatch.setattr(urllib3, "PoolManager", FailingPoolManager)
    app = create_app(str(tmp_path / "workshop.db"), str(tmp_path / "uploads"))
    with TestClient(app) as client:
        response = client.get("/api/backend-health", headers=headers())
    assert response.status_code == 200
    assert response.json()["status"] == 0
    assert response.json()["body"] == "Backend health check unavailable"


def test_backend_health_returns_generic_error_for_invalid_utf8(monkeypatch, tmp_path: Path) -> None:
    class InvalidUtf8PoolManager:
        def request(self, method: str, url: str, timeout: float) -> SimpleNamespace:
            return SimpleNamespace(status=200, data=b"\xff")

    monkeypatch.setattr(urllib3, "PoolManager", InvalidUtf8PoolManager)
    app = create_app(str(tmp_path / "workshop.db"), str(tmp_path / "uploads"))
    with TestClient(app) as client:
        response = client.get("/api/backend-health", headers=headers())
    assert response.status_code == 200
    assert response.json() == {
        "requestedBy": "student",
        "status": 0,
        "body": "Backend health check unavailable",
    }


@pytest.mark.parametrize(
    ("method", "path", "request_data"),
    [
        ("get", "/api/tasks", {}),
        ("post", "/api/tasks", {"json": {}}),
        ("get", "/api/summary", {}),
        (
            "post",
            "/api/requirements",
            {"files": {"file": ("requirements.txt", b"", "text/plain")}},
        ),
        ("get", "/api/backend-health", {}),
    ],
)
def test_every_endpoint_rejects_missing_authorization(
    method: str, path: str, request_data: dict, tmp_path: Path
) -> None:
    app = create_app(str(tmp_path / "workshop.db"), str(tmp_path / "uploads"))
    with TestClient(app) as client:
        response = getattr(client, method)(path, **request_data)
    assert response.status_code == 401
    assert response.json() == {"detail": "Invalid token"}


@pytest.mark.parametrize(
    ("method", "path", "request_data", "repository_method"),
    [
        ("get", "/api/tasks", {}, "list_by_owner"),
        ("post", "/api/tasks", {"json": {}}, "create"),
        ("get", "/api/summary", {}, "summary_by_owner"),
    ],
)
def test_task_endpoints_return_generic_internal_error(
    method: str,
    path: str,
    request_data: dict,
    repository_method: str,
    tmp_path: Path,
) -> None:
    app = create_app(str(tmp_path / "workshop.db"), str(tmp_path / "uploads"))

    def raise_database_error(*args, **kwargs):
        raise RuntimeError("database details must not reach the client")

    setattr(app.state.task_repository, repository_method, raise_database_error)
    with TestClient(app, raise_server_exceptions=False) as client:
        response = getattr(client, method)(path, headers=headers(), **request_data)
    assert response.status_code == 500
    assert response.text == "Internal Server Error"


def test_upload_returns_generic_internal_error_for_write_failure(tmp_path: Path) -> None:
    app = create_app(str(tmp_path / "workshop.db"), str(tmp_path / "uploads"))
    upload_directory_file = tmp_path / "not-a-directory"
    upload_directory_file.write_text("block directory creation", encoding="utf-8")
    app.dependency_overrides[get_upload_directory] = lambda: str(upload_directory_file)
    with TestClient(app, raise_server_exceptions=False) as client:
        response = client.post(
            "/api/requirements",
            headers=headers(),
            files={"file": ("requirements.txt", b"valid text", "text/plain")},
        )
    assert response.status_code == 500
    assert response.text == "Internal Server Error"


def test_backend_health_returns_generic_internal_error_for_unexpected_failure(
    monkeypatch, tmp_path: Path
) -> None:
    class UnexpectedPoolManager:
        def request(self, method: str, url: str, timeout: float) -> None:
            raise RuntimeError("unexpected upstream detail")

    monkeypatch.setattr(urllib3, "PoolManager", UnexpectedPoolManager)
    app = create_app(str(tmp_path / "workshop.db"), str(tmp_path / "uploads"))
    with TestClient(app, raise_server_exceptions=False) as client:
        response = client.get("/api/backend-health", headers=headers())
    assert response.status_code == 500
    assert response.text == "Internal Server Error"


def test_upload_rejects_missing_file_with_validation_error(tmp_path: Path) -> None:
    app = create_app(str(tmp_path / "workshop.db"), str(tmp_path / "uploads"))
    with TestClient(app) as client:
        response = client.post("/api/requirements", headers=headers())
    assert response.status_code == 422
    assert response.json()["detail"][0]["loc"] == ["body", "file"]


def test_upload_rejects_filename_without_extension(tmp_path: Path) -> None:
    app = create_app(str(tmp_path / "workshop.db"), str(tmp_path / "uploads"))
    with TestClient(app) as client:
        response = client.post(
            "/api/requirements",
            headers=headers(),
            files={"file": ("requirements", b"text", "text/plain")},
        )
    assert response.status_code == 400
    assert response.json() == {"detail": "Unsupported file extension"}


@pytest.mark.parametrize("content_size", [0, 1024 * 1024])
def test_upload_accepts_empty_and_maximum_size_files(
    content_size: int, tmp_path: Path
) -> None:
    upload_dir = tmp_path / "uploads"
    app = create_app(str(tmp_path / "workshop.db"), str(upload_dir))
    content = b"x" * content_size
    with TestClient(app) as client:
        response = client.post(
            "/api/requirements",
            headers=headers(),
            files={"file": ("requirements.txt", content, "text/plain")},
        )
    assert response.status_code == 201
    assert response.json()["size"] == content_size
    assert (upload_dir / "requirements.txt").read_bytes() == content


def test_backend_health_preserves_non_success_upstream_status(monkeypatch, tmp_path: Path) -> None:
    class UnhealthyPoolManager:
        def request(self, method: str, url: str, timeout: float) -> SimpleNamespace:
            return SimpleNamespace(status=503, data=b"maintenance")

    monkeypatch.setattr(urllib3, "PoolManager", UnhealthyPoolManager)
    app = create_app(str(tmp_path / "workshop.db"), str(tmp_path / "uploads"))
    with TestClient(app) as client:
        response = client.get("/api/backend-health", headers=headers())
    assert response.status_code == 200
    assert response.json() == {
        "requestedBy": "student",
        "status": 503,
        "body": "maintenance",
    }

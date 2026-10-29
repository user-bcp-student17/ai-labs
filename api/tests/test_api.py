import base64
import logging
import time
from pathlib import Path
from types import SimpleNamespace

import jwt
import urllib3
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from fastapi.testclient import TestClient
import pytest

from app.main import create_app
from app.routes import get_upload_directory


JWT_ISSUER = "https://issuer.test"
JWT_AUDIENCE = "workshop-api"
TEST_PRIVATE_KEY = rsa.generate_private_key(public_exponent=65537, key_size=2048)
OTHER_PRIVATE_KEY = rsa.generate_private_key(public_exponent=65537, key_size=2048)
TEST_PUBLIC_KEY = TEST_PRIVATE_KEY.public_key().public_bytes(
    serialization.Encoding.PEM,
    serialization.PublicFormat.SubjectPublicKeyInfo,
).decode("ascii")


@pytest.fixture(autouse=True)
def configure_jwt_environment(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("AUTH_JWT_PUBLIC_KEY", TEST_PUBLIC_KEY)
    monkeypatch.setenv("AUTH_JWT_ISSUER", JWT_ISSUER)
    monkeypatch.setenv("AUTH_JWT_AUDIENCE", JWT_AUDIENCE)


def token(
    username: str = "student",
    role: str = "STUDENT",
    signing_key=TEST_PRIVATE_KEY,
    omit_claims: tuple[str, ...] = (),
    **claim_overrides: object,
) -> str:
    claims: dict[str, object] = {
        "sub": username,
        "role": role,
        "iss": JWT_ISSUER,
        "aud": JWT_AUDIENCE,
        "exp": int(time.time()) + 3600,
    }
    claims.update(claim_overrides)
    for claim_name in omit_claims:
        claims.pop(claim_name, None)
    return jwt.encode(claims, signing_key, algorithm="RS256")


def headers(username: str = "student", role: str = "STUDENT") -> dict[str, str]:
    return {"Authorization": f"Bearer {token(username, role)}"}


def test_accepts_configured_rs256_jwt(
    tmp_path: Path, configure_jwt_environment: None
) -> None:
    encoded_token = token()
    app = create_app(str(tmp_path / "workshop.db"), str(tmp_path / "uploads"))
    with TestClient(app) as client:
        response = client.get(
            "/api/tasks", headers={"Authorization": f"Bearer {encoded_token}"}
        )
    assert response.status_code == 200
    assert response.json()[0]["owner"] == "student"


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


@pytest.mark.parametrize(
    ("claim_name", "claim_value"),
    [
        ("exp", 1),
        ("iss", "https://unexpected.test"),
        ("aud", "another-api"),
    ],
)
def test_rejects_jwt_with_invalid_registered_claim(
    claim_name: str, claim_value: object, tmp_path: Path
) -> None:
    app = create_app(str(tmp_path / "workshop.db"), str(tmp_path / "uploads"))
    with TestClient(app) as client:
        response = client.get(
            "/api/tasks",
            headers={"Authorization": f"Bearer {token(**{claim_name: claim_value})}"},
        )
    assert response.status_code == 401
    assert response.json() == {"detail": "Invalid token"}


def test_rejects_jwt_signed_by_another_key(tmp_path: Path) -> None:
    app = create_app(str(tmp_path / "workshop.db"), str(tmp_path / "uploads"))
    with TestClient(app) as client:
        response = client.get(
            "/api/tasks",
            headers={
                "Authorization": f"Bearer {token(signing_key=OTHER_PRIVATE_KEY)}"
            },
        )
    assert response.status_code == 401
    assert response.json() == {"detail": "Invalid token"}


@pytest.mark.parametrize("claim_name", ("sub", "iss", "aud", "exp"))
def test_rejects_jwt_missing_required_claim(claim_name: str, tmp_path: Path) -> None:
    app = create_app(str(tmp_path / "workshop.db"), str(tmp_path / "uploads"))
    with TestClient(app) as client:
        response = client.get(
            "/api/tasks",
            headers={
                "Authorization": f"Bearer {token(omit_claims=(claim_name,))}"
            },
        )
    assert response.status_code == 401
    assert response.json() == {"detail": "Invalid token"}


def test_rejects_legacy_base64_token(tmp_path: Path) -> None:
    legacy_token = base64.b64encode(b"legacy-format-token").decode("ascii")
    app = create_app(str(tmp_path / "workshop.db"), str(tmp_path / "uploads"))
    with TestClient(app) as client:
        response = client.get(
            "/api/tasks", headers={"Authorization": f"Bearer {legacy_token}"}
        )
    assert response.status_code == 401
    assert response.json() == {"detail": "Invalid token"}


def test_missing_jwt_configuration_fails_closed(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.delenv("AUTH_JWT_PUBLIC_KEY")
    app = create_app(str(tmp_path / "workshop.db"), str(tmp_path / "uploads"))
    with TestClient(app) as client:
        response = client.get("/api/tasks", headers=headers())
    assert response.status_code == 503
    assert response.json() == {
        "detail": "Authentication configuration unavailable"
    }


def test_missing_authorization_returns_401_without_jwt_configuration(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.delenv("AUTH_JWT_PUBLIC_KEY")
    monkeypatch.delenv("AUTH_JWT_ISSUER")
    monkeypatch.delenv("AUTH_JWT_AUDIENCE")
    app = create_app(str(tmp_path / "workshop.db"), str(tmp_path / "uploads"))
    with TestClient(app) as client:
        response = client.get("/api/tasks")
    assert response.status_code == 401
    assert response.json() == {"detail": "Invalid token"}


@pytest.mark.parametrize(
    ("method", "path", "request_data", "expected_status"),
    [
        ("get", "/api/tasks", {}, 200),
        ("post", "/api/tasks", {"json": {}}, 201),
        ("get", "/api/summary", {}, 200),
        (
            "post",
            "/api/requirements",
            {"files": {"file": ("requirements.txt", b"text", "text/plain")}},
            201,
        ),
        ("get", "/api/backend-health", {}, 200),
    ],
)
def test_valid_jwt_without_role_reaches_every_protected_route(
    method: str,
    path: str,
    request_data: dict,
    expected_status: int,
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    class HealthyPoolManager:
        def request(self, *args: object, **kwargs: object) -> SimpleNamespace:
            return SimpleNamespace(status=200, data=b"ok")

    monkeypatch.setattr(urllib3, "PoolManager", HealthyPoolManager)
    app = create_app(str(tmp_path / "workshop.db"), str(tmp_path / "uploads"))
    with TestClient(app) as client:
        response = getattr(client, method)(
            path,
            headers={"Authorization": f"Bearer {token(omit_claims=('role',))}"},
            **request_data,
        )
    assert response.status_code == expected_status


@pytest.mark.parametrize(
    "authorization",
    ["Basic c3R1ZGVudDpXb3Jrc2hvcDEyMyE=", "Bearer", "Bearer two parts", "Token abc"],
)
def test_rejects_malformed_authorization_without_creating_task(
    authorization: str, tmp_path: Path
) -> None:
    app = create_app(str(tmp_path / "workshop.db"), str(tmp_path / "uploads"))
    repository = app.state.task_repository
    with TestClient(app) as client:
        tasks_before = len(repository.list_by_owner("student"))
        response = client.post(
            "/api/tasks",
            headers={"Authorization": authorization},
            json={"title": "Blocked"},
        )
        tasks_after = len(repository.list_by_owner("student"))
    assert response.status_code == 401
    assert response.json() == {"detail": "Invalid token"}
    assert tasks_after == tasks_before


@pytest.mark.parametrize("variable_name", ("AUTH_JWT_ISSUER", "AUTH_JWT_AUDIENCE"))
def test_missing_jwt_issuer_or_audience_fails_closed(
    variable_name: str, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.delenv(variable_name)
    app = create_app(str(tmp_path / "workshop.db"), str(tmp_path / "uploads"))
    with TestClient(app) as client:
        response = client.get("/api/tasks", headers=headers())
    assert response.status_code == 503
    assert response.json() == {
        "detail": "Authentication configuration unavailable"
    }


def test_unusable_jwt_public_key_fails_closed(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.setenv("AUTH_JWT_PUBLIC_KEY", "not-a-pem-key")
    app = create_app(str(tmp_path / "workshop.db"), str(tmp_path / "uploads"))
    with TestClient(app) as client:
        response = client.get("/api/tasks", headers=headers())
    assert response.status_code == 503
    assert response.json() == {
        "detail": "Authentication configuration unavailable"
    }


def test_accepts_jwt_when_pem_newlines_are_escaped(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.setenv("AUTH_JWT_PUBLIC_KEY", TEST_PUBLIC_KEY.replace("\n", "\\n"))
    app = create_app(str(tmp_path / "workshop.db"), str(tmp_path / "uploads"))
    with TestClient(app) as client:
        response = client.get("/api/tasks", headers=headers())
    assert response.status_code == 200


def test_authentication_failures_do_not_log_credentials_or_key(
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
    capsys: pytest.CaptureFixture[str],
    tmp_path: Path,
) -> None:
    caplog.set_level(logging.DEBUG)
    rejected_token = token(signing_key=OTHER_PRIVATE_KEY)
    app = create_app(str(tmp_path / "workshop.db"), str(tmp_path / "uploads"))
    with TestClient(app) as client:
        client.get("/api/tasks", headers={"Authorization": f"Bearer {rejected_token}"})
        monkeypatch.delenv("AUTH_JWT_ISSUER")
        client.get("/api/tasks", headers={"Authorization": f"Bearer {rejected_token}"})
    captured = capsys.readouterr()
    output = caplog.text + captured.out + captured.err
    assert rejected_token not in output
    assert TEST_PUBLIC_KEY not in output
    assert "BEGIN PUBLIC KEY" not in output


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

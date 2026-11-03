import tempfile
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.config import MAX_MULTIPART_OVERHEAD_BYTES
from tests.test_upload_security import MAX_FILE_BYTES, upload
from tests.tokens import auth, bearer, make_token

MULTIPART_HEADERS = {"Content-Type": "multipart/form-data; boundary=boundary"}
ALLOWED_ORIGIN = "http://localhost:4200"

REJECTED_AUTHORIZATION = {
    "absent": {},
    "empty-bearer": {"Authorization": "Bearer "},
    "wrong-scheme": {"Authorization": "Token " + make_token()},
    "wrong-secret": bearer(make_token(secret="another-test-only-secret-0123456789abcdef")),
    "expired": bearer(make_token(ttl=-60)),
    "wrong-issuer": bearer(make_token(issuer="other-issuer")),
    "wrong-audience": bearer(make_token(audience="other-audience")),
    "missing-subject": bearer(make_token(omit=("sub",))),
    "malformed": {"Authorization": "Bearer not-a-jwt"},
}


@pytest.fixture
def spool_files(monkeypatch: pytest.MonkeyPatch) -> list[str]:
    created: list[str] = []
    real_temporary_file = tempfile.TemporaryFile

    def recording_temporary_file(*args, **kwargs):
        created.append("spool")
        return real_temporary_file(*args, **kwargs)

    monkeypatch.setattr("app.upload_limit.tempfile.TemporaryFile", recording_temporary_file)
    return created


def oversized_body() -> bytes:
    return b"--boundary\r\n" + b"x" * (MAX_FILE_BYTES + MAX_MULTIPART_OVERHEAD_BYTES + 1) + b"\r\n--boundary--\r\n"


def post_oversized(client: TestClient, headers: dict[str, str]):
    return client.post("/api/requirements", headers={**headers, **MULTIPART_HEADERS}, content=oversized_body())


@pytest.mark.parametrize("headers", REJECTED_AUTHORIZATION.values(), ids=REJECTED_AUTHORIZATION.keys())
def test_rejected_credentials_get_401_without_spooling_the_body(
    client: TestClient, tmp_path: Path, spool_files: list[str], headers: dict[str, str]
) -> None:
    response = post_oversized(client, headers)
    assert (response.status_code, response.json()) == (401, {"detail": "Invalid token"})
    assert spool_files == []
    assert list((tmp_path / "uploads").iterdir()) == []


def test_streamed_body_without_credentials_is_not_read(client: TestClient, spool_files: list[str]) -> None:
    consumed = 0

    def body():
        nonlocal consumed
        for _ in range(90):
            consumed += 1
            yield b"x" * 65536

    response = client.post("/api/requirements", headers=MULTIPART_HEADERS, content=body())
    assert response.status_code == 401
    assert spool_files == []
    assert consumed < 90


def test_missing_server_secret_fails_closed_without_spooling(
    client: TestClient, monkeypatch: pytest.MonkeyPatch, spool_files: list[str]
) -> None:
    monkeypatch.delenv("WORKSHOP_JWT_SECRET")
    response = post_oversized(client, auth())
    assert response.status_code == 500
    assert spool_files == []


def test_valid_credentials_still_spool_and_store_the_file(
    client: TestClient, tmp_path: Path, spool_files: list[str]
) -> None:
    response = upload(client, "valid.txt", b"content")
    assert response.status_code == 201
    assert spool_files == ["spool"]
    assert (tmp_path / "uploads" / "valid.txt").read_bytes() == b"content"


def test_valid_credentials_over_limit_still_get_413(client: TestClient, tmp_path: Path) -> None:
    response = post_oversized(client, auth())
    assert (response.status_code, response.json()) == (413, {"detail": "Request too large"})
    assert list((tmp_path / "uploads").iterdir()) == []


def test_unauthenticated_rejection_keeps_cors_headers(client: TestClient) -> None:
    response = post_oversized(client, {"Origin": ALLOWED_ORIGIN})
    assert response.status_code == 401
    assert response.headers["access-control-allow-origin"] == ALLOWED_ORIGIN


def test_preflight_for_upload_is_not_authenticated(client: TestClient) -> None:
    response = client.options(
        "/api/requirements",
        headers={
            "Origin": ALLOWED_ORIGIN,
            "Access-Control-Request-Method": "POST",
            "Access-Control-Request-Headers": "Authorization",
        },
    )
    assert response.status_code == 200
    assert response.headers["access-control-allow-origin"] == ALLOWED_ORIGIN


@pytest.mark.parametrize(
    "headers",
    [*REJECTED_AUTHORIZATION.values(), auth(), auth("trainer", "TRAINER")],
    ids=[*REJECTED_AUTHORIZATION.keys(), "valid-student", "valid-trainer"],
)
def test_upload_and_task_routes_agree_on_the_token_decision(client: TestClient, headers: dict[str, str]) -> None:
    upload_rejected = post_oversized(client, headers).status_code == 401
    tasks_rejected = client.get("/api/tasks", headers=headers).status_code == 401
    assert upload_rejected == tasks_rejected

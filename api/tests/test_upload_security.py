import asyncio
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from starlette.datastructures import UploadFile
from starlette.types import Message, Receive, Scope, Send

from app.upload_limit import UploadRequestLimit
from tests.tokens import auth

MAX_FILE_BYTES = 5 * 1024 * 1024


def upload(client: TestClient, name: str, content: bytes, username: str = "student"):
    body = (
        b'--boundary\r\nContent-Disposition: form-data; name="file"; filename="'
        + name.encode("utf-8")
        + b'"\r\nContent-Type: application/octet-stream\r\n\r\n'
        + content
        + b"\r\n--boundary--\r\n"
    )
    return client.post(
        "/api/requirements",
        headers={**auth(username), "Content-Type": "multipart/form-data; boundary=boundary"},
        content=body,
    )


@pytest.mark.parametrize(
    "filename",
    ["../escape.txt", r"..\escape.txt", "/absolute.txt", "folder/file.txt", r"folder\file.txt",
     "C:escape.txt", "CON.txt", "bad\x00name.txt", "x" * 300 + ".txt"],
)
def test_rejects_unsafe_names(client: TestClient, tmp_path: Path, filename: str) -> None:
    response = upload(client, filename, b"content")
    assert response.status_code == 400
    assert list((tmp_path / "uploads").iterdir()) == []
    assert not (tmp_path / "escape.txt").exists()


@pytest.mark.parametrize("filename", ["document.exe", "README", "document.txt.exe"])
def test_rejects_disallowed_extensions(client: TestClient, tmp_path: Path, filename: str) -> None:
    assert upload(client, filename, b"x").status_code == 415
    assert list((tmp_path / "uploads").iterdir()) == []


@pytest.mark.parametrize("filename", ["document.txt", "document.MD", "document.pdf", "document.docx"])
def test_allowed_extensions_return_relative_reference(client: TestClient, tmp_path: Path, filename: str) -> None:
    response = upload(client, filename, b"content")
    assert response.status_code == 201
    assert response.json() == {"owner": "student", "fileName": filename, "storedAt": filename, "size": 7}
    assert (tmp_path / "uploads" / filename).read_bytes() == b"content"


@pytest.mark.parametrize("size", [0, MAX_FILE_BYTES - 1, MAX_FILE_BYTES])
def test_accepts_files_at_or_below_limit(client: TestClient, tmp_path: Path, size: int) -> None:
    response = upload(client, "allowed.txt", b"a" * size)
    assert response.status_code == 201
    assert response.json()["size"] == size
    assert (tmp_path / "uploads" / "allowed.txt").stat().st_size == size


def test_rejects_file_over_limit_without_partial_file(client: TestClient, tmp_path: Path) -> None:
    response = upload(client, "large.txt", b"a" * (MAX_FILE_BYTES + 1))
    assert response.status_code == 413
    assert list((tmp_path / "uploads").iterdir()) == []


def test_request_without_content_length_is_bounded_before_multipart_parsing(
    client: TestClient, tmp_path: Path
) -> None:
    def body():
        yield b"--boundary\r\nContent-Disposition: form-data; name=\"extra\"\r\n\r\n"
        for _ in range(90):
            yield b"x" * 65536
        yield b"\r\n--boundary--\r\n"

    response = client.post(
        "/api/requirements",
        headers={**auth(), "Content-Type": "multipart/form-data; boundary=boundary"},
        content=body(),
    )
    assert response.status_code == 413
    assert list((tmp_path / "uploads").iterdir()) == []


def test_conflicts_do_not_overwrite_between_users(client: TestClient, tmp_path: Path) -> None:
    assert upload(client, "same.txt", b"first").status_code == 201
    assert upload(client, "same.txt", b"second", "trainer").status_code == 409
    assert (tmp_path / "uploads" / "same.txt").read_bytes() == b"first"


def test_concurrent_conflicts_have_one_winner(client: TestClient, tmp_path: Path) -> None:
    with ThreadPoolExecutor(max_workers=2) as pool:
        responses = list(pool.map(lambda value: upload(client, "same.txt", value), [b"one", b"two"]))
    assert sorted(response.status_code for response in responses) == [201, 409]
    assert (tmp_path / "uploads" / "same.txt").read_bytes() in {b"one", b"two"}
    assert sorted(path.name for path in (tmp_path / "uploads").iterdir()) == ["same.txt"]


def test_existing_symlink_is_not_followed(client: TestClient, tmp_path: Path) -> None:
    outside = tmp_path / "outside.txt"
    outside.write_bytes(b"untouched")
    link = tmp_path / "uploads" / "link.txt"
    try:
        link.symlink_to(outside)
    except OSError as error:
        pytest.skip(f"Symlink creation unavailable: {error}")
    assert upload(client, "link.txt", b"overwrite").status_code == 409
    assert outside.read_bytes() == b"untouched"


def test_read_failure_removes_partial_file(client: TestClient, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    calls = 0

    async def failing_read(self: UploadFile, size: int = -1) -> bytes:
        nonlocal calls
        calls += 1
        if calls == 1:
            return b"partial"
        raise OSError("test read error")

    monkeypatch.setattr(UploadFile, "read", failing_read)
    assert upload(client, "failure.txt", b"input").status_code == 500
    assert list((tmp_path / "uploads").iterdir()) == []


def test_storage_failure_removes_partial_file(client: TestClient, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    def failing_link(source: Path, destination: Path) -> None:
        raise OSError("test storage error")

    monkeypatch.setattr("app.uploads.os.link", failing_link)
    assert upload(client, "failure.txt", b"input").status_code == 500
    assert list((tmp_path / "uploads").iterdir()) == []


def test_streaming_limit_stops_reading_before_application() -> None:
    async def run() -> None:
        received = 0
        messages: list[Message] = []
        app_called = False

        async def app(scope: Scope, receive: Receive, send: Send) -> None:
            nonlocal app_called
            app_called = True

        async def receive() -> Message:
            nonlocal received
            received += 1
            return {"type": "http.request", "body": b"x" * 65536, "more_body": True}

        async def send(message: Message) -> None:
            messages.append(message)

        scope: Scope = {
            "type": "http",
            "method": "POST",
            "path": "/api/requirements",
            "headers": [(b"authorization", auth()["Authorization"].encode("latin-1"))],
        }
        await UploadRequestLimit(app)(scope, receive, send)
        assert not app_called
        assert received == 82
        assert messages[0]["status"] == 413

    asyncio.run(run())

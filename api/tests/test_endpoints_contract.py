"""Pruebas por endpoint según docs/ENDPOINTS.md (sección api): camino feliz, casos borde y errores."""

import re
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from tests.test_characterization import health_server
from tests.tokens import auth, bearer, make_token

CREATED_AT_FORMAT = re.compile(r"^\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}$")
FIRST_CREATED_TASK_ID = 4
INVALID_TOKEN = {"detail": "Invalid token"}
FORBIDDEN_OWNER = {"detail": "Access to another owner is forbidden"}
TEXT_FILE = ("requirements.txt", b"Login must be accessible", "text/plain")

ENDPOINTS = [
    ("get", "/api/tasks"),
    ("post", "/api/tasks"),
    ("get", "/api/summary"),
    ("post", "/api/requirements"),
    ("get", "/api/backend-health"),
]


def _upload(client: TestClient, file: tuple[str, bytes, str], headers: dict[str, str] | None = None):
    return client.post("/api/requirements", headers=headers or auth(), files={"file": file})


def _without_created_at(task: dict[str, object]) -> dict[str, object]:
    return {key: value for key, value in task.items() if key != "createdAt"}


# ---------------------------------------------------------------- GET /api/tasks


def test_get_tasks_happy_path_trainer_sees_only_own_task(client: TestClient) -> None:
    response = client.get("/api/tasks", headers=auth("trainer"))
    assert response.status_code == 200
    assert [_without_created_at(task) for task in response.json()] == [
        {"id": 3, "title": "Trainer notes", "description": "Preparar retrospectiva", "status": "TODO", "owner": "trainer", "priority": "LOW"}
    ]
    assert CREATED_AT_FORMAT.match(response.json()[0]["createdAt"])


def test_get_tasks_edge_user_without_tasks_gets_empty_list(client: TestClient) -> None:
    response = client.get("/api/tasks", headers=auth("nobody"))
    assert (response.status_code, response.json()) == (200, [])


def test_get_tasks_edge_bearer_scheme_is_case_insensitive(client: TestClient) -> None:
    headers = {"Authorization": "bearer " + make_token()}
    assert client.get("/api/tasks", headers=headers).status_code == 200


def test_get_tasks_edge_created_tasks_are_listed_after_seed_in_id_order(client: TestClient) -> None:
    client.post("/api/tasks", headers=auth(), json={"title": "first"})
    client.post("/api/tasks", headers=auth(), json={"title": "second"})
    ids = [task["id"] for task in client.get("/api/tasks", headers=auth()).json()]
    assert ids == [1, 2, 4, 5]


def test_get_tasks_edge_tasks_created_by_one_user_are_invisible_to_another(client: TestClient) -> None:
    client.post("/api/tasks", headers=auth(), json={"title": "private"})
    titles = [task["title"] for task in client.get("/api/tasks", headers=auth("trainer")).json()]
    assert titles == ["Trainer notes"]


def test_get_tasks_error_401_without_authorization_header(client: TestClient) -> None:
    response = client.get("/api/tasks")
    assert (response.status_code, response.json()) == (401, INVALID_TOKEN)


def test_get_tasks_error_403_user_cannot_read_tasks_of_another_owner(client: TestClient) -> None:
    response = client.get("/api/tasks", params={"owner": "trainer"}, headers=auth())
    assert (response.status_code, response.json()) == (403, FORBIDDEN_OWNER)
    assert "Trainer notes" not in response.text


def test_get_tasks_error_403_empty_owner_is_forbidden(client: TestClient) -> None:
    response = client.get("/api/tasks", params={"owner": ""}, headers=auth())
    assert (response.status_code, response.json()) == (403, FORBIDDEN_OWNER)


# --------------------------------------------------------------- POST /api/tasks


def test_post_tasks_happy_path_creates_and_persists_task(client: TestClient) -> None:
    payload = {"title": "Write docs", "description": "Document the API", "status": "IN_PROGRESS", "priority": "HIGH"}
    response = client.post("/api/tasks", headers=auth(), json=payload)
    assert response.status_code == 201
    assert _without_created_at(response.json()) == {"id": FIRST_CREATED_TASK_ID, "owner": "student", **payload}
    assert CREATED_AT_FORMAT.match(response.json()["createdAt"])
    listed = client.get("/api/tasks", headers=auth()).json()
    assert _without_created_at(listed[-1]) == _without_created_at(response.json())


def test_post_tasks_edge_empty_object_uses_defaults(client: TestClient) -> None:
    response = client.post("/api/tasks", headers=auth(), json={})
    assert response.status_code == 201
    assert _without_created_at(response.json()) == {
        "id": FIRST_CREATED_TASK_ID, "title": "", "description": "", "status": "TODO", "owner": "student", "priority": "MEDIUM",
    }


def test_post_tasks_edge_unknown_fields_are_ignored(client: TestClient) -> None:
    response = client.post("/api/tasks", headers=auth(), json={"title": "x", "unexpected": 1})
    assert response.status_code == 201
    assert "unexpected" not in response.json()


def test_post_tasks_edge_null_owner_means_own_user(client: TestClient) -> None:
    response = client.post("/api/tasks", headers=auth(), json={"title": "x", "owner": None})
    assert (response.status_code, response.json()["owner"]) == (201, "student")


def test_post_tasks_edge_unicode_and_long_text_are_stored_intact(client: TestClient) -> None:
    title = "Revisión ñandú 日本語 " + "x" * 5000
    created = client.post("/api/tasks", headers=auth(), json={"title": title}).json()
    assert created["title"] == title
    assert client.get("/api/tasks", headers=auth()).json()[-1]["title"] == title


def test_post_tasks_error_401_without_token_even_with_invalid_body(client: TestClient) -> None:
    response = client.post("/api/tasks", json={"title": ["x"]})
    assert (response.status_code, response.json()) == (401, INVALID_TOKEN)


def test_post_tasks_error_403_creating_for_another_owner(client: TestClient) -> None:
    response = client.post("/api/tasks", headers=auth(), json={"title": "x", "owner": "trainer"})
    assert (response.status_code, response.json()) == (403, FORBIDDEN_OWNER)
    assert len(client.get("/api/tasks", headers=auth("trainer")).json()) == 1


def test_post_tasks_error_403_empty_owner_is_forbidden(client: TestClient) -> None:
    response = client.post("/api/tasks", headers=auth(), json={"owner": ""})
    assert (response.status_code, response.json()) == (403, FORBIDDEN_OWNER)


@pytest.mark.parametrize(
    ("body", "error_type", "location"),
    [
        ({"title": ["x"]}, "string_type", ["body", "title"]),
        ({"title": None}, "string_type", ["body", "title"]),
        ({"description": 5}, "string_type", ["body", "description"]),
        ({"status": None}, "string_type", ["body", "status"]),
        ({"priority": {"a": 1}}, "string_type", ["body", "priority"]),
        ({"owner": 7}, "string_type", ["body", "owner"]),
    ],
    ids=["title-list", "title-null", "description-number", "status-null", "priority-object", "owner-number"],
)
def test_post_tasks_error_422_field_with_wrong_type(client: TestClient, body: dict, error_type: str, location: list[str]) -> None:
    response = client.post("/api/tasks", headers=auth(), json=body)
    assert response.status_code == 422
    error = response.json()["detail"][0]
    assert (error["type"], error["loc"]) == (error_type, location)


def test_post_tasks_error_422_without_body(client: TestClient) -> None:
    response = client.post("/api/tasks", headers=auth())
    assert response.status_code == 422
    assert response.json()["detail"][0]["type"] == "missing"
    assert response.json()["detail"][0]["loc"] == ["body"]


def test_post_tasks_error_422_malformed_json(client: TestClient) -> None:
    response = client.post("/api/tasks", headers={**auth(), "Content-Type": "application/json"}, content=b"{bad")
    assert response.status_code == 422
    assert response.json()["detail"][0]["type"] == "json_invalid"


def test_post_tasks_error_422_form_body_instead_of_json(client: TestClient) -> None:
    response = client.post("/api/tasks", headers=auth(), data={"title": "x"})
    assert response.status_code == 422
    assert response.json()["detail"][0]["type"] == "model_attributes_type"


def test_post_tasks_422_does_not_create_a_task(client: TestClient) -> None:
    client.post("/api/tasks", headers=auth(), json={"title": None})
    assert len(client.get("/api/tasks", headers=auth()).json()) == 2


# ------------------------------------------------------------- GET /api/summary


def test_get_summary_happy_path_after_creating_tasks(client: TestClient) -> None:
    client.post("/api/tasks", headers=auth(), json={"title": "a", "status": "DONE", "priority": "HIGH"})
    client.post("/api/tasks", headers=auth(), json={"title": "b", "status": "TODO", "priority": "HIGH"})
    assert client.get("/api/summary", headers=auth()).json() == {
        "owner": "student", "total": 4, "byStatus": {"TODO": 2, "IN_PROGRESS": 1, "DONE": 1}, "highPriorityOpen": 2,
    }


def test_get_summary_edge_user_without_tasks(client: TestClient) -> None:
    response = client.get("/api/summary", headers=auth("nobody"))
    assert (response.status_code, response.json()) == (200, {"owner": "nobody", "total": 0, "byStatus": {}, "highPriorityOpen": 0})


def test_get_summary_edge_other_users_tasks_are_not_counted(client: TestClient) -> None:
    client.post("/api/tasks", headers=auth("trainer"), json={"title": "t", "priority": "HIGH"})
    assert client.get("/api/summary", headers=auth()).json()["total"] == 2
    assert client.get("/api/summary", headers=auth("trainer")).json()["total"] == 2


def test_get_summary_edge_free_text_status_is_counted_and_priority_is_case_sensitive(client: TestClient) -> None:
    client.post("/api/tasks", headers=auth("nobody"), json={"title": "t", "status": "custom", "priority": "high"})
    body = client.get("/api/summary", headers=auth("nobody")).json()
    assert (body["byStatus"], body["highPriorityOpen"]) == ({"custom": 1}, 0)


def test_get_summary_error_401_without_token(client: TestClient) -> None:
    response = client.get("/api/summary")
    assert (response.status_code, response.json()) == (401, INVALID_TOKEN)


def test_get_summary_error_403_user_cannot_read_summary_of_another_owner(client: TestClient) -> None:
    response = client.get("/api/summary", params={"owner": "trainer"}, headers=auth())
    assert (response.status_code, response.json()) == (403, FORBIDDEN_OWNER)


def test_get_summary_error_403_empty_owner_is_forbidden(client: TestClient) -> None:
    response = client.get("/api/summary", params={"owner": ""}, headers=auth())
    assert (response.status_code, response.json()) == (403, FORBIDDEN_OWNER)


# ------------------------------------------------------- POST /api/requirements


def test_post_requirements_happy_path_stores_file_and_returns_contract(client: TestClient, tmp_path: Path) -> None:
    response = _upload(client, TEXT_FILE)
    assert response.status_code == 201
    assert response.json() == {
        "owner": "student",
        "fileName": "requirements.txt",
        "storedAt": "requirements.txt",
        "size": 24,
    }
    assert (tmp_path / "uploads" / "requirements.txt").read_bytes() == TEXT_FILE[1]


def test_post_requirements_edge_file_without_extension_is_rejected(client: TestClient, tmp_path: Path) -> None:
    response = _upload(client, ("README", b"no extension", "application/octet-stream"))
    assert response.status_code == 415
    assert not (tmp_path / "uploads" / "README").exists()


def test_post_requirements_edge_empty_file_has_size_zero(client: TestClient, tmp_path: Path) -> None:
    response = _upload(client, ("empty.txt", b"", "text/plain"))
    assert (response.status_code, response.json()["size"]) == (201, 0)
    assert (tmp_path / "uploads" / "empty.txt").read_bytes() == b""


def test_post_requirements_edge_binary_content_is_stored_byte_for_byte(client: TestClient, tmp_path: Path) -> None:
    content = bytes(range(256)) * 4096
    response = _upload(client, ("data.pdf", content, "application/octet-stream"))
    assert (response.status_code, response.json()["size"]) == (201, 1024 * 1024)
    assert (tmp_path / "uploads" / "data.pdf").read_bytes() == content


def test_post_requirements_edge_file_with_same_name_is_not_overwritten(client: TestClient, tmp_path: Path) -> None:
    assert _upload(client, ("same.txt", b"first", "text/plain")).status_code == 201
    assert _upload(client, ("same.txt", b"second", "text/plain")).status_code == 409
    assert (tmp_path / "uploads" / "same.txt").read_bytes() == b"first"


def test_post_requirements_edge_filename_with_spaces(client: TestClient, tmp_path: Path) -> None:
    response = _upload(client, ("my requirements v1.txt", b"x", "text/plain"))
    assert (response.status_code, response.json()["fileName"]) == (201, "my requirements v1.txt")
    assert (tmp_path / "uploads" / "my requirements v1.txt").exists()


def test_post_requirements_error_401_without_token(client: TestClient, tmp_path: Path) -> None:
    response = client.post("/api/requirements", files={"file": TEXT_FILE})
    assert (response.status_code, response.json()) == (401, INVALID_TOKEN)
    assert not (tmp_path / "uploads" / "requirements.txt").exists()


def test_post_requirements_error_401_with_invalid_token(client: TestClient) -> None:
    response = _upload(client, TEXT_FILE, bearer("not-a-token"))
    assert (response.status_code, response.json()) == (401, INVALID_TOKEN)


def test_post_requirements_error_422_without_file_field(client: TestClient) -> None:
    response = client.post("/api/requirements", headers=auth())
    assert response.status_code == 422
    assert response.json()["detail"][0]["loc"] == ["body", "file"]
    assert response.json()["detail"][0]["type"] == "missing"


def test_post_requirements_error_422_part_without_filename(client: TestClient) -> None:
    response = _upload(client, ("", b"x", "text/plain"))
    assert response.status_code == 422
    assert response.json()["detail"][0]["loc"] == ["body", "file"]


def test_post_requirements_security_traversal_name_stays_inside_upload_dir(client: TestClient, tmp_path: Path) -> None:
    assert _upload(client, ("../escape.txt", b"x", "text/plain")).status_code == 400
    assert not (tmp_path / "escape.txt").exists()


# ------------------------------------------------------ GET /api/backend-health


def test_get_backend_health_happy_path_relays_upstream_json(client: TestClient, monkeypatch: pytest.MonkeyPatch) -> None:
    with health_server(200, b'{"status":"UP","checks":[]}') as url:
        monkeypatch.setenv("AUTH_HEALTH_URL", url)
        response = client.get("/api/backend-health", headers=auth("trainer"))
    assert (response.status_code, response.json()) == (
        200,
        {"requestedBy": "trainer", "status": 200, "body": '{"status":"UP","checks":[]}'},
    )


def test_get_backend_health_edge_upstream_error_status_is_relayed_with_http_200(client: TestClient, monkeypatch: pytest.MonkeyPatch) -> None:
    with health_server(503, b"DOWN") as url:
        monkeypatch.setenv("AUTH_HEALTH_URL", url)
        response = client.get("/api/backend-health", headers=auth())
    assert (response.status_code, response.json()) == (200, {"requestedBy": "student", "status": 503, "body": "DOWN"})


def test_get_backend_health_edge_empty_upstream_body(client: TestClient, monkeypatch: pytest.MonkeyPatch) -> None:
    with health_server(204, b"") as url:
        monkeypatch.setenv("AUTH_HEALTH_URL", url)
        body = client.get("/api/backend-health", headers=auth()).json()
    assert (body["status"], body["body"]) == (204, "")


def test_get_backend_health_edge_non_utf8_body_is_decoded_with_replacement(client: TestClient, monkeypatch: pytest.MonkeyPatch) -> None:
    with health_server(200, b"ok \xff\xfe") as url:
        monkeypatch.setenv("AUTH_HEALTH_URL", url)
        response = client.get("/api/backend-health", headers=auth())
    assert (response.status_code, response.json()["body"]) == (200, "ok \ufffd\ufffd")


def test_get_backend_health_edge_unreachable_backend_returns_http_200_status_zero(client: TestClient, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("AUTH_HEALTH_URL", "http://127.0.0.1:1/q/health")
    response = client.get("/api/backend-health", headers=auth())
    assert (response.status_code, response.json()) == (200, {"requestedBy": "student", "status": 0, "body": "Backend unavailable"})


def test_get_backend_health_error_401_without_token(client: TestClient) -> None:
    response = client.get("/api/backend-health")
    assert (response.status_code, response.json()) == (401, INVALID_TOKEN)


def test_get_backend_health_client_cannot_choose_the_url(client: TestClient, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("AUTH_HEALTH_URL", "http://127.0.0.1:1/q/health")
    response = client.get("/api/backend-health", params={"url": "http://example.invalid"}, headers=auth())
    assert response.json()["body"] == "Backend unavailable"


# ------------------------------------------- errores comunes a todos los endpoints


@pytest.mark.parametrize(("method", "path"), ENDPOINTS)
def test_every_endpoint_error_500_when_jwt_secret_is_not_configured(
    client: TestClient, monkeypatch: pytest.MonkeyPatch, method: str, path: str
) -> None:
    headers = auth()
    monkeypatch.delenv("WORKSHOP_JWT_SECRET")
    response = getattr(client, method)(path, headers=headers)
    assert response.status_code == 500
    assert response.text == "Internal Server Error"
    assert response.headers["content-type"].startswith("text/plain")


@pytest.mark.parametrize(("method", "path"), ENDPOINTS)
def test_every_endpoint_error_401_body_is_generic_for_invalid_tokens(client: TestClient, method: str, path: str) -> None:
    for headers in (bearer("not-a-token"), bearer(make_token(ttl=-10)), {"Authorization": "Basic abc"}):
        response = getattr(client, method)(path, headers=headers)
        assert (response.status_code, response.json()) == (401, INVALID_TOKEN)


@pytest.mark.parametrize(("method", "path"), [("delete", "/api/tasks"), ("put", "/api/summary"), ("get", "/api/requirements"), ("post", "/api/backend-health")])
def test_error_405_for_methods_not_offered(client: TestClient, method: str, path: str) -> None:
    response = getattr(client, method)(path, headers=auth())
    assert (response.status_code, response.json()) == (405, {"detail": "Method Not Allowed"})

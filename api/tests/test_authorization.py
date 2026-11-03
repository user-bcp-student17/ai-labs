import pytest
from fastapi.testclient import TestClient

from tests.tokens import auth


@pytest.mark.parametrize("path", ["/api/tasks", "/api/summary"])
def test_h_api_02_reading_another_owner_is_forbidden(client: TestClient, path: str) -> None:
    response = client.get(path, params={"owner": "trainer"}, headers=auth())
    assert response.status_code == 403
    assert "trainer" not in response.text


def test_h_api_02_creating_a_task_for_another_owner_is_forbidden(client: TestClient) -> None:
    response = client.post("/api/tasks", headers=auth(), json={"title": "x", "owner": "trainer"})
    assert response.status_code == 403
    assert client.get("/api/tasks", headers=auth("trainer")).json()[0]["title"] == "Trainer notes"
    assert len(client.get("/api/tasks", headers=auth("trainer")).json()) == 1


def test_h_api_02_each_identity_only_sees_its_own_data(client: TestClient) -> None:
    assert [task["title"] for task in client.get("/api/tasks", headers=auth("trainer")).json()] == ["Trainer notes"]
    assert client.get("/api/summary", headers=auth("trainer")).json()["owner"] == "trainer"


def test_h_api_02_explicit_owner_equal_to_identity_is_still_accepted(client: TestClient) -> None:
    response = client.post("/api/tasks", headers=auth(), json={"title": "mine", "owner": "student"})
    assert (response.status_code, response.json()["owner"]) == (201, "student")


def test_h_api_02_role_does_not_grant_access_to_other_owners(client: TestClient) -> None:
    response = client.get("/api/tasks", params={"owner": "student"}, headers=auth("trainer", "TRAINER"))
    assert response.status_code == 403

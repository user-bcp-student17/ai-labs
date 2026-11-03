from fastapi.testclient import TestClient

from tests.tokens import auth

INJECTION_OWNER = "x' OR '1'='1"


def test_h_api_03_quote_in_title_is_stored_literally(client: TestClient) -> None:
    created = client.post("/api/tasks", headers=auth(), json={"title": "O'Neil", "description": "it's ok"})
    assert created.status_code == 201
    assert (created.json()["title"], created.json()["description"]) == ("O'Neil", "it's ok")
    titles = [task["title"] for task in client.get("/api/tasks", headers=auth()).json()]
    assert "O'Neil" in titles


def test_h_api_03_sql_metacharacters_in_every_field_do_not_alter_other_rows(client: TestClient) -> None:
    payload = {"title": "a'); DELETE FROM tasks; --", "description": "d", "status": "x' OR '1'='1", "priority": "p'"}
    assert client.post("/api/tasks", headers=auth(), json=payload).status_code == 201
    assert len(client.get("/api/tasks", headers=auth()).json()) == 3
    assert [task["title"] for task in client.get("/api/tasks", params={"owner": "trainer"}, headers=auth("trainer")).json()] == [
        "Trainer notes"
    ]


def test_h_api_03_owner_filter_is_a_value_not_sql(client: TestClient) -> None:
    assert client.get("/api/tasks", headers=auth(INJECTION_OWNER)).json() == []


def test_h_api_03_summary_filter_is_a_value_not_sql(client: TestClient) -> None:
    assert client.get("/api/summary", headers=auth(INJECTION_OWNER)).json()["total"] == 0

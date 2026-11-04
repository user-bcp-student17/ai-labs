import threading
import warnings
from pathlib import Path

from fastapi.testclient import TestClient

from app.main import create_app
from tests.tokens import auth

APP_DIR = Path(__file__).resolve().parent.parent / "app"


def test_h_api_08_sql_lives_only_in_the_repository() -> None:
    offenders = [
        path.name
        for path in APP_DIR.rglob("*.py")
        if path.name != "repository.py" and ("execute(" in path.read_text(encoding="utf-8") or "import sqlite3" in path.read_text(encoding="utf-8"))
    ]
    assert offenders == []
    assert (APP_DIR / "repository.py").exists()


def test_h_api_08_main_only_wires_the_app() -> None:
    assert len((APP_DIR / "main.py").read_text(encoding="utf-8").splitlines()) < 60


def test_h_api_09_openapi_exposes_typed_models(tmp_path: Path) -> None:
    schemas = create_app(str(tmp_path / "w.db"), str(tmp_path / "u")).openapi()["components"]["schemas"]
    assert {"TaskCreate", "TaskResponse", "SummaryResponse", "UploadResponse", "HealthResponse"} <= set(schemas)
    assert "createdAt" in schemas["TaskResponse"]["properties"]
    assert {"byStatus", "highPriorityOpen"} <= set(schemas["SummaryResponse"]["properties"])


def test_h_api_09_non_string_fields_are_rejected(client: TestClient) -> None:
    assert client.post("/api/tasks", headers=auth(), json={"title": ["not", "text"]}).status_code == 422


def test_h_api_10_uses_lifespan_instead_of_deprecated_on_event(tmp_path: Path) -> None:
    with warnings.catch_warnings():
        warnings.simplefilter("error", DeprecationWarning)
        app = create_app(str(tmp_path / "w.db"), str(tmp_path / "u"))
        with TestClient(app) as client:
            assert client.get("/api/tasks", headers=auth()).status_code == 200
    assert app.router.on_shutdown == []


def test_h_api_10_concurrent_requests_do_not_share_a_connection(tmp_path: Path) -> None:
    app = create_app(str(tmp_path / "w.db"), str(tmp_path / "u"))
    statuses: list[int] = []

    def read_tasks(test_client: TestClient) -> None:
        for _ in range(10):
            statuses.append(test_client.get("/api/tasks", headers=auth()).status_code)

    with TestClient(app) as client:
        threads = [threading.Thread(target=read_tasks, args=(client,)) for _ in range(4)]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join()
    assert statuses == [200] * 40

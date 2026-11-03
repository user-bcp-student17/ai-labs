from pathlib import Path

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.main import create_app
from tests.tokens import TEST_AUDIENCE, TEST_ISSUER, TEST_SECRET


@pytest.fixture(autouse=True)
def jwt_environment(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("WORKSHOP_JWT_SECRET", TEST_SECRET)
    monkeypatch.setenv("WORKSHOP_JWT_ISSUER", TEST_ISSUER)
    monkeypatch.setenv("WORKSHOP_JWT_AUDIENCE", TEST_AUDIENCE)


@pytest.fixture
def app(tmp_path: Path) -> FastAPI:
    return create_app(str(tmp_path / "workshop.db"), str(tmp_path / "uploads"))


@pytest.fixture
def client(app: FastAPI):
    with TestClient(app, raise_server_exceptions=False) as test_client:
        yield test_client

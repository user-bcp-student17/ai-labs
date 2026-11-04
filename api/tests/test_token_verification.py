import base64
import json
import time

import pytest
from fastapi.testclient import TestClient

from tests.tokens import auth, bearer, make_token


def _unsigned_token() -> str:
    def part(data: dict[str, object]) -> str:
        return base64.urlsafe_b64encode(json.dumps(data).encode()).rstrip(b"=").decode()

    claims = {"sub": "student", "role": "STUDENT", "exp": int(time.time()) + 3600, "iss": "reqflow-auth", "aud": "reqflow-api"}
    return part({"alg": "none", "typ": "JWT"}) + "." + part(claims) + "."


def _legacy_token() -> str:
    raw = f"student|STUDENT|{int(time.time()) + 3600}|WORKSHOP_SECRET_2026"
    return base64.b64encode(raw.encode()).decode()


def _status(client: TestClient, headers: dict[str, str]) -> int:
    return client.get("/api/tasks", headers=headers).status_code


def test_h_api_01_valid_signed_token_is_accepted(client: TestClient) -> None:
    response = client.get("/api/summary", headers=auth("trainer", "TRAINER"))
    assert (response.status_code, response.json()["owner"]) == (200, "trainer")


def test_h_api_01_legacy_base64_token_is_rejected(client: TestClient) -> None:
    assert _status(client, bearer(_legacy_token())) == 401


@pytest.mark.parametrize(
    "token",
    [
        make_token(secret="another-secret-that-is-long-enough-0123456789"),
        make_token(ttl=-10),
        make_token(issuer="someone-else"),
        make_token(audience="another-api"),
        make_token(omit=("exp",)),
        make_token(omit=("iss",)),
        make_token(omit=("aud",)),
        make_token(omit=("sub",)),
        make_token(omit=("role",)),
        make_token(algorithm="HS384"),
        _unsigned_token(),
        "not-a-token",
    ],
    ids=["bad-signature", "expired", "bad-issuer", "bad-audience", "no-exp", "no-iss", "no-aud", "no-sub", "no-role", "other-alg", "alg-none", "garbage"],
)
def test_h_api_01_invalid_tokens_are_rejected(client: TestClient, token: str) -> None:
    assert _status(client, bearer(token)) == 401


@pytest.mark.parametrize("header", ["", "Basic abc", "Bearer", "Bearer "])
def test_h_api_01_missing_or_malformed_authorization_is_rejected(client: TestClient, header: str) -> None:
    assert _status(client, {"Authorization": header}) == 401


def test_h_api_01_token_without_scheme_is_rejected(client: TestClient) -> None:
    assert _status(client, {"Authorization": make_token()}) == 401


def test_h_api_01_embedded_secret_is_gone() -> None:
    from pathlib import Path

    source = "".join(path.read_text(encoding="utf-8") for path in (Path(__file__).parent.parent / "app").rglob("*.py"))
    assert "WORKSHOP_SECRET_2026" not in source


def test_h_api_01_missing_secret_fails_closed(client: TestClient, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("WORKSHOP_JWT_SECRET")
    assert _status(client, auth()) == 500


def test_h_api_06_invalid_token_detail_is_generic(client: TestClient) -> None:
    response = client.get("/api/tasks", headers=bearer("not-a-token"))
    assert response.json() == {"detail": "Invalid token"}

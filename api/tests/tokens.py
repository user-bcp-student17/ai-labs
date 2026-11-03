import time

import jwt

TEST_SECRET = "test-only-secret-not-for-production-use-0123456789"
TEST_ISSUER = "reqflow-auth"
TEST_AUDIENCE = "reqflow-api"


def make_token(
    username: str = "student",
    role: str = "STUDENT",
    ttl: int = 3600,
    secret: str = TEST_SECRET,
    issuer: str | None = TEST_ISSUER,
    audience: str | None = TEST_AUDIENCE,
    algorithm: str = "HS256",
    omit: tuple[str, ...] = (),
) -> str:
    claims = {"sub": username, "role": role, "exp": int(time.time()) + ttl, "iss": issuer, "aud": audience}
    payload = {name: value for name, value in claims.items() if name not in omit and value is not None}
    return jwt.encode(payload, secret, algorithm=algorithm)


def bearer(token: str) -> dict[str, str]:
    return {"Authorization": "Bearer " + token}


def auth(username: str = "student", role: str = "STUDENT") -> dict[str, str]:
    return bearer(make_token(username, role))

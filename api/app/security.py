import os

import jwt
from fastapi import Header, HTTPException


JWT_ALGORITHM = "RS256"
JWT_REQUIRED_CLAIMS = ("exp", "iss", "aud", "sub")
JWT_PUBLIC_KEY_ENV = "AUTH_JWT_PUBLIC_KEY"
JWT_ISSUER_ENV = "AUTH_JWT_ISSUER"
JWT_AUDIENCE_ENV = "AUTH_JWT_AUDIENCE"
INVALID_TOKEN_DETAIL = "Invalid token"
AUTHENTICATION_UNAVAILABLE_DETAIL = "Authentication configuration unavailable"


def _jwt_configuration() -> tuple[str, str, str] | None:
    public_key = os.getenv(JWT_PUBLIC_KEY_ENV, "").replace("\\n", "\n").strip()
    issuer = os.getenv(JWT_ISSUER_ENV, "").strip()
    audience = os.getenv(JWT_AUDIENCE_ENV, "").strip()
    if not public_key or not issuer or not audience:
        return None
    return public_key, issuer, audience


def verified_identity(authorization: str = Header(default="")) -> dict[str, str]:
    scheme, separator, token = authorization.partition(" ")
    if scheme.lower() != "bearer" or not separator or not token or " " in token:
        raise HTTPException(status_code=401, detail=INVALID_TOKEN_DETAIL)

    configuration = _jwt_configuration()
    if configuration is None:
        raise HTTPException(
            status_code=503, detail=AUTHENTICATION_UNAVAILABLE_DETAIL
        )

    public_key, issuer, audience = configuration
    try:
        claims = jwt.decode(
            token,
            public_key,
            algorithms=[JWT_ALGORITHM],
            audience=audience,
            issuer=issuer,
            options={"require": JWT_REQUIRED_CLAIMS},
        )
    except jwt.InvalidKeyError as error:
        raise HTTPException(
            status_code=503, detail=AUTHENTICATION_UNAVAILABLE_DETAIL
        ) from error
    except jwt.PyJWTError as error:
        raise HTTPException(status_code=401, detail=INVALID_TOKEN_DETAIL) from error

    username = claims.get("sub")
    if not isinstance(username, str) or not username.strip():
        raise HTTPException(status_code=401, detail=INVALID_TOKEN_DETAIL)
    role = claims.get("role")
    return {"username": username, "role": role if isinstance(role, str) else ""}


def ensure_owner_access(owner: str, identity: dict[str, str]) -> str:
    if owner != identity["username"]:
        raise HTTPException(status_code=403, detail="Owner access denied")
    return owner
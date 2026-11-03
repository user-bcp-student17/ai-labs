import logging

import jwt
from fastapi import Header, HTTPException
from pydantic import ValidationError

from app.config import JWT_ALGORITHMS, JWT_REQUIRED_CLAIMS, jwt_settings
from app.schemas import Identity

BEARER_SCHEME = "bearer"
INVALID_TOKEN_DETAIL = "Invalid token"
FORBIDDEN_OWNER_DETAIL = "Access to another owner is forbidden"

logger = logging.getLogger(__name__)


def _extract_bearer_token(authorization: str) -> str:
    scheme, _, token = authorization.partition(" ")
    if scheme.lower() != BEARER_SCHEME or not token.strip():
        raise ValueError("missing bearer token")
    return token.strip()


def _verify_token(token: str) -> Identity:
    settings = jwt_settings()
    claims = jwt.decode(
        token,
        settings.secret,
        algorithms=JWT_ALGORITHMS,
        audience=settings.audience,
        issuer=settings.issuer,
        options={"require": JWT_REQUIRED_CLAIMS},
    )
    return Identity(username=claims["sub"], role=claims["role"])


def current_identity(authorization: str = Header(default="")) -> Identity:
    try:
        return _verify_token(_extract_bearer_token(authorization))
    except (ValueError, jwt.PyJWTError, ValidationError) as error:
        logger.warning("Rejected token: %s", error)
        raise HTTPException(status_code=401, detail=INVALID_TOKEN_DETAIL) from error


def authorize_owner(requested_owner: str | None, identity: Identity) -> str:
    if requested_owner is not None and requested_owner != identity.username:
        raise HTTPException(status_code=403, detail=FORBIDDEN_OWNER_DETAIL)
    return identity.username

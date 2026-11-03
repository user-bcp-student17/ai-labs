import os
from dataclasses import dataclass

ENV_DB_PATH = "WORKSHOP_DB_PATH"
ENV_UPLOAD_DIR = "WORKSHOP_UPLOAD_DIR"
ENV_AUTH_HEALTH_URL = "AUTH_HEALTH_URL"

DEFAULT_DB_PATH = "./data/workshop.db"
DEFAULT_UPLOAD_DIR = "./uploads"
DEFAULT_AUTH_HEALTH_URL = "http://localhost:8080/q/health"
ENV_CORS_ORIGINS = "WORKSHOP_CORS_ORIGINS"
DEFAULT_CORS_ORIGINS = "http://localhost:4200"
CORS_ALLOWED_METHODS = ["GET", "POST", "OPTIONS"]
CORS_ALLOWED_HEADERS = ["Authorization", "Content-Type"]

HEALTH_TIMEOUT_SECONDS = 3.0
BACKEND_UNAVAILABLE_BODY = "Backend unavailable"

ALLOWED_UPLOAD_EXTENSIONS = frozenset({".txt", ".md", ".pdf", ".docx"})
MAX_UPLOAD_BYTES = 5 * 1024 * 1024
MAX_MULTIPART_OVERHEAD_BYTES = 64 * 1024
UPLOAD_CHUNK_BYTES = 64 * 1024
MAX_FILENAME_BYTES = 255

DEFAULT_TASK_STATUS = "TODO"
DEFAULT_TASK_PRIORITY = "MEDIUM"
HIGH_PRIORITY = "HIGH"
CLOSED_STATUSES = frozenset({"DONE", "ARCHIVED"})

ENV_JWT_SECRET = "WORKSHOP_JWT_SECRET"
ENV_JWT_ISSUER = "WORKSHOP_JWT_ISSUER"
ENV_JWT_AUDIENCE = "WORKSHOP_JWT_AUDIENCE"
DEFAULT_JWT_ISSUER = "reqflow-auth"
DEFAULT_JWT_AUDIENCE = "reqflow-api"
JWT_ALGORITHMS = ["HS256"]
JWT_REQUIRED_CLAIMS = ["exp", "iss", "aud", "sub", "role"]


class MissingJwtSecretError(RuntimeError):
    pass


@dataclass(frozen=True)
class JwtSettings:
    secret: str
    issuer: str
    audience: str


def jwt_settings() -> JwtSettings:
    secret = os.getenv(ENV_JWT_SECRET)
    if not secret:
        raise MissingJwtSecretError(ENV_JWT_SECRET + " is not configured")
    return JwtSettings(
        secret=secret,
        issuer=os.getenv(ENV_JWT_ISSUER, DEFAULT_JWT_ISSUER),
        audience=os.getenv(ENV_JWT_AUDIENCE, DEFAULT_JWT_AUDIENCE),
    )


def auth_health_url() -> str:
    return os.getenv(ENV_AUTH_HEALTH_URL, DEFAULT_AUTH_HEALTH_URL)


def cors_origins() -> list[str]:
    configured = os.getenv(ENV_CORS_ORIGINS, DEFAULT_CORS_ORIGINS)
    return [origin.strip() for origin in configured.split(",") if origin.strip()]

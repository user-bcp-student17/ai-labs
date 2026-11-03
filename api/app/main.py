import os
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import (
    CORS_ALLOWED_HEADERS,
    CORS_ALLOWED_METHODS,
    DEFAULT_DB_PATH,
    DEFAULT_UPLOAD_DIR,
    ENV_DB_PATH,
    ENV_UPLOAD_DIR,
    cors_origins,
)
from app.repository import TaskRepository
from app.routes import health, requirements, tasks
from app.upload_limit import UploadRequestLimit


def _initialize_database(db_path: str) -> None:
    repository = TaskRepository.open(db_path)
    try:
        repository.initialize()
    finally:
        repository.close()


def create_app(db_path: str | None = None, upload_dir: str | None = None) -> FastAPI:
    selected_db = db_path or os.getenv(ENV_DB_PATH, DEFAULT_DB_PATH)
    selected_uploads = upload_dir or os.getenv(ENV_UPLOAD_DIR, DEFAULT_UPLOAD_DIR)
    Path(selected_db).parent.mkdir(parents=True, exist_ok=True)
    Path(selected_uploads).mkdir(parents=True, exist_ok=True)
    _initialize_database(selected_db)

    app = FastAPI(title="Workshop Requirements API", version="0.1.0")
    app.state.db_path = selected_db
    app.state.upload_dir = selected_uploads
    app.add_middleware(UploadRequestLimit)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=cors_origins(),
        allow_credentials=True,
        allow_methods=CORS_ALLOWED_METHODS,
        allow_headers=CORS_ALLOWED_HEADERS,
    )
    for router_module in (tasks, requirements, health):
        app.include_router(router_module.router)
    return app


app = create_app()

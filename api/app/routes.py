import os

import urllib3
from fastapi import APIRouter, Body, Depends, File, Query, Request, UploadFile

from app.repositories import TaskRepository
from app.schemas import (
    BackendHealthResponse,
    CreateTaskRequest,
    RequirementResponse,
    SummaryResponse,
    TaskResponse,
)
from app.security import ensure_owner_access, verified_identity
from app.services import as_task, summarize_tasks
from app.upload_service import store_requirement


router = APIRouter()
BACKEND_HEALTH_TIMEOUT_SECONDS = 3.0
BACKEND_HEALTH_ERROR_MESSAGE = "Backend health check unavailable"


def get_task_repository(request: Request) -> TaskRepository:
    return request.app.state.task_repository


def get_upload_directory(request: Request) -> str:
    return request.app.state.upload_dir


@router.get("/api/tasks", response_model=list[TaskResponse])
def list_tasks(
    owner: str | None = Query(default=None),
    identity: dict[str, str] = Depends(verified_identity),
    repository: TaskRepository = Depends(get_task_repository),
) -> list[TaskResponse]:
    requested_owner = ensure_owner_access(owner or identity["username"], identity)
    rows = repository.list_by_owner(requested_owner)
    return [as_task(row) for row in rows]


@router.post("/api/tasks", status_code=201, response_model=TaskResponse)
def create_task(
    payload: CreateTaskRequest = Body(...),
    identity: dict[str, str] = Depends(verified_identity),
    repository: TaskRepository = Depends(get_task_repository),
) -> TaskResponse:
    owner = ensure_owner_access(payload.owner or identity["username"], identity)
    row = repository.create(payload.title, payload.description, payload.status, owner, payload.priority)
    return as_task(row)


@router.get("/api/summary", response_model=SummaryResponse)
def summary(
    owner: str | None = Query(default=None),
    identity: dict[str, str] = Depends(verified_identity),
    repository: TaskRepository = Depends(get_task_repository),
) -> SummaryResponse:
    requested_owner = ensure_owner_access(owner or identity["username"], identity)
    rows = repository.summary_by_owner(requested_owner)
    return summarize_tasks(requested_owner, rows)


@router.post("/api/requirements", status_code=201, response_model=RequirementResponse)
async def upload_requirement(
    file: UploadFile = File(...),
    identity: dict[str, str] = Depends(verified_identity),
    upload_directory: str = Depends(get_upload_directory),
) -> RequirementResponse:
    stored = await store_requirement(file, upload_directory)
    return RequirementResponse(
        owner=identity["username"],
        fileName=stored.filename,
        storedAt=stored.path,
        size=stored.size,
    )


@router.get("/api/backend-health", response_model=BackendHealthResponse)
def backend_health(identity: dict[str, str] = Depends(verified_identity)) -> BackendHealthResponse:
    url = os.getenv("AUTH_HEALTH_URL", "http://localhost:8080/q/health")
    try:
        response = urllib3.PoolManager().request(
            "GET", url, timeout=BACKEND_HEALTH_TIMEOUT_SECONDS
        )
        return BackendHealthResponse(
            requestedBy=identity["username"],
            status=response.status,
            body=response.data.decode("utf-8"),
        )
    except (urllib3.exceptions.HTTPError, UnicodeDecodeError):
        return BackendHealthResponse(
            requestedBy=identity["username"],
            status=0,
            body=BACKEND_HEALTH_ERROR_MESSAGE,
        )
from fastapi import APIRouter, Depends, Query

from app import services
from app.dependencies import get_task_repository
from app.repository import TaskRepository
from app.schemas import Identity, SummaryResponse, TaskCreate, TaskResponse
from app.security import authorize_owner, current_identity

router = APIRouter(prefix="/api")


@router.get("/tasks")
def list_tasks(
    owner: str | None = Query(default=None),
    identity: Identity = Depends(current_identity),
    repository: TaskRepository = Depends(get_task_repository),
) -> list[TaskResponse]:
    return services.list_tasks(repository, authorize_owner(owner, identity))


@router.post("/tasks", status_code=201)
def create_task(
    payload: TaskCreate,
    identity: Identity = Depends(current_identity),
    repository: TaskRepository = Depends(get_task_repository),
) -> TaskResponse:
    return services.create_task(repository, authorize_owner(payload.owner, identity), payload)


@router.get("/summary")
def summary(
    owner: str | None = Query(default=None),
    identity: Identity = Depends(current_identity),
    repository: TaskRepository = Depends(get_task_repository),
) -> SummaryResponse:
    return services.summarize(repository, authorize_owner(owner, identity))

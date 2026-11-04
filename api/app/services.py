import logging
from collections import Counter
import urllib3

from app.config import BACKEND_UNAVAILABLE_BODY, CLOSED_STATUSES, HEALTH_TIMEOUT_SECONDS, HIGH_PRIORITY
from app.repository import TaskRepository
from app.schemas import HealthResponse, Identity, SummaryResponse, TaskCreate, TaskResponse

_http = urllib3.PoolManager()
logger = logging.getLogger(__name__)


def list_tasks(repository: TaskRepository, owner: str) -> list[TaskResponse]:
    return repository.list_by_owner(owner)


def create_task(repository: TaskRepository, owner: str, payload: TaskCreate) -> TaskResponse:
    return repository.add(owner, payload)


def _is_open_high_priority(status: str, priority: str) -> bool:
    return priority == HIGH_PRIORITY and status not in CLOSED_STATUSES


def summarize(repository: TaskRepository, owner: str) -> SummaryResponse:
    rows = repository.status_and_priority_by_owner(owner)
    return SummaryResponse(
        owner=owner,
        total=len(rows),
        by_status=dict(Counter(status for status, _ in rows)),
        high_priority_open=sum(_is_open_high_priority(status, priority) for status, priority in rows),
    )


def check_backend_health(url: str, identity: Identity) -> HealthResponse:
    try:
        response = _http.request("GET", url, timeout=HEALTH_TIMEOUT_SECONDS)
    except urllib3.exceptions.HTTPError as error:
        logger.warning("Backend health check failed: %s", error)
        return HealthResponse(requested_by=identity.username, status=0, body=BACKEND_UNAVAILABLE_BODY)
    return HealthResponse(
        requested_by=identity.username, status=response.status, body=response.data.decode("utf-8", errors="replace")
    )

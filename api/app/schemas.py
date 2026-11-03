from pydantic import BaseModel, Field

from app.config import DEFAULT_TASK_PRIORITY, DEFAULT_TASK_STATUS


class Identity(BaseModel):
    username: str
    role: str


class TaskCreate(BaseModel):
    title: str = ""
    description: str = ""
    status: str = DEFAULT_TASK_STATUS
    priority: str = DEFAULT_TASK_PRIORITY
    owner: str | None = None


class TaskResponse(BaseModel):
    id: int
    title: str
    description: str
    status: str
    owner: str
    priority: str
    created_at: str = Field(serialization_alias="createdAt")


class SummaryResponse(BaseModel):
    owner: str
    total: int
    by_status: dict[str, int] = Field(serialization_alias="byStatus")
    high_priority_open: int = Field(serialization_alias="highPriorityOpen")


class UploadResponse(BaseModel):
    owner: str
    file_name: str | None = Field(serialization_alias="fileName")
    stored_at: str = Field(serialization_alias="storedAt")
    size: int


class HealthResponse(BaseModel):
    requested_by: str = Field(serialization_alias="requestedBy")
    status: int
    body: str

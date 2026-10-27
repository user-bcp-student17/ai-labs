from typing import Any

from pydantic import BaseModel, ConfigDict, Field, model_validator


class CreateTaskRequest(BaseModel):
    title: str = ""
    description: str = ""
    status: str = "TODO"
    priority: str = "MEDIUM"
    owner: str | None = None

    @model_validator(mode="before")
    @classmethod
    def preserve_legacy_string_conversion(cls, value: Any) -> Any:
        if not isinstance(value, dict):
            return value
        normalized = dict(value)
        defaults = {
            "title": "",
            "description": "",
            "status": "TODO",
            "priority": "MEDIUM",
        }
        for field, default in defaults.items():
            normalized[field] = str(normalized.get(field, default))
        if "owner" in normalized:
            normalized["owner"] = str(normalized["owner"])
        return normalized


class TaskResponse(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    id: int
    title: str
    description: str
    status: str
    owner: str
    priority: str
    created_at: str = Field(alias="createdAt")


class SummaryResponse(BaseModel):
    owner: str
    total: int
    byStatus: dict[str, int]
    highPriorityOpen: int


class RequirementResponse(BaseModel):
    owner: str
    fileName: str
    storedAt: str
    size: int


class BackendHealthResponse(BaseModel):
    requestedBy: str
    status: int
    body: str
import sqlite3

from app.schemas import SummaryResponse, TaskResponse


def as_task(row: sqlite3.Row) -> TaskResponse:
    return TaskResponse(
        id=row["id"],
        title=row["title"],
        description=row["description"],
        status=row["status"],
        owner=row["owner"],
        priority=row["priority"],
        createdAt=row["created_at"],
    )


def summarize_tasks(owner: str, rows: list[sqlite3.Row]) -> SummaryResponse:
    by_status: dict[str, int] = {}
    high_priority_open = 0
    for row in rows:
        status = row["status"]
        by_status[status] = by_status.get(status, 0) + 1
        if row["priority"] == "HIGH" and status not in {"DONE", "ARCHIVED"}:
            high_priority_open += 1
    return SummaryResponse(
        owner=owner,
        total=len(rows),
        byStatus=by_status,
        highPriorityOpen=high_priority_open,
    )
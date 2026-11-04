from collections.abc import Iterator

from fastapi import Request

from app.repository import TaskRepository


def get_task_repository(request: Request) -> Iterator[TaskRepository]:
    repository = TaskRepository.open(request.app.state.db_path)
    try:
        yield repository
    finally:
        repository.close()


def get_upload_dir(request: Request) -> str:
    return request.app.state.upload_dir

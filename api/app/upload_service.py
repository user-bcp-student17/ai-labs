from dataclasses import dataclass
from pathlib import Path, PurePosixPath, PureWindowsPath

from fastapi import HTTPException, UploadFile


MAX_REQUIREMENT_SIZE_BYTES = 1024 * 1024
ALLOWED_REQUIREMENT_EXTENSIONS = frozenset({".txt"})


@dataclass(frozen=True)
class StoredRequirement:
    filename: str
    path: str
    size: int


def validate_requirement_filename(filename: str | None) -> str:
    if (
        not filename
        or "\x00" in filename
        or PurePosixPath(filename).name != filename
        or PureWindowsPath(filename).name != filename
    ):
        raise HTTPException(status_code=400, detail="Invalid file name")
    if PurePosixPath(filename).suffix.lower() not in ALLOWED_REQUIREMENT_EXTENSIONS:
        raise HTTPException(status_code=400, detail="Unsupported file extension")
    return filename


async def store_requirement(file: UploadFile, upload_dir: str) -> StoredRequirement:
    filename = validate_requirement_filename(file.filename)
    content = await file.read(MAX_REQUIREMENT_SIZE_BYTES + 1)
    if len(content) > MAX_REQUIREMENT_SIZE_BYTES:
        raise HTTPException(status_code=413, detail="File is too large")

    target = Path(upload_dir) / filename
    target.write_bytes(content)
    return StoredRequirement(filename=filename, path=str(target), size=len(content))
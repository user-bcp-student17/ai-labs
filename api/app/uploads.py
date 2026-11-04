import os
import tempfile
import unicodedata
from pathlib import Path

from fastapi import HTTPException, UploadFile

from app.config import ALLOWED_UPLOAD_EXTENSIONS, MAX_FILENAME_BYTES, MAX_UPLOAD_BYTES, UPLOAD_CHUNK_BYTES
from app.schemas import Identity, UploadResponse

INVALID_FILENAME_CHARS = frozenset('/\\<>:"|?*')
RESERVED_NAMES = frozenset(
    {"CON", "PRN", "AUX", "NUL"}
    | {f"COM{number}" for number in range(1, 10)}
    | {f"LPT{number}" for number in range(1, 10)}
)


def validated_filename(filename: str | None) -> str:
    if not filename:
        raise HTTPException(status_code=400, detail="Invalid filename")
    name = unicodedata.normalize("NFC", filename)
    if (
        name in {".", ".."}
        or name[-1] in {" ", "."}
        or len(name.encode("utf-8")) > MAX_FILENAME_BYTES
        or any(char in INVALID_FILENAME_CHARS or unicodedata.category(char) == "Cc" for char in name)
        or name.split(".", 1)[0].upper() in RESERVED_NAMES
    ):
        raise HTTPException(status_code=400, detail="Invalid filename")
    if Path(name).suffix.lower() not in ALLOWED_UPLOAD_EXTENSIONS:
        raise HTTPException(status_code=415, detail="File extension not allowed")
    return name


async def store_requirement(upload: UploadFile, upload_dir: str, identity: Identity) -> UploadResponse:
    filename = validated_filename(upload.filename)
    directory = Path(upload_dir).resolve(strict=True)
    descriptor, temporary_name = tempfile.mkstemp(prefix=".upload-", dir=directory)
    temporary_path = Path(temporary_name)
    size = 0
    try:
        with os.fdopen(descriptor, "wb") as target:
            while chunk := await upload.read(UPLOAD_CHUNK_BYTES):
                size += len(chunk)
                if size > MAX_UPLOAD_BYTES:
                    raise HTTPException(status_code=413, detail="File too large")
                target.write(chunk)
        try:
            os.link(temporary_path, directory / filename)
        except FileExistsError as error:
            raise HTTPException(status_code=409, detail="File already exists") from error
    finally:
        temporary_path.unlink()
    return UploadResponse(owner=identity.username, file_name=filename, stored_at=filename, size=size)

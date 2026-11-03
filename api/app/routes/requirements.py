from fastapi import APIRouter, Depends, File, UploadFile

from app import uploads
from app.dependencies import get_upload_dir
from app.schemas import Identity, UploadResponse
from app.security import current_identity

router = APIRouter(prefix="/api")


@router.post("/requirements", status_code=201)
async def upload_requirement(
    file: UploadFile = File(...),
    identity: Identity = Depends(current_identity),
    upload_dir: str = Depends(get_upload_dir),
) -> UploadResponse:
    return await uploads.store_requirement(file, upload_dir, identity)

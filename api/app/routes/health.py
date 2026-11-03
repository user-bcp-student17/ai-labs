from fastapi import APIRouter, Depends

from app import services
from app.config import auth_health_url
from app.schemas import HealthResponse, Identity
from app.security import current_identity

router = APIRouter(prefix="/api")


@router.get("/backend-health")
def backend_health(identity: Identity = Depends(current_identity)) -> HealthResponse:
    return services.check_backend_health(auth_health_url(), identity)

from fastapi import APIRouter

from app.schemas.common import HealthResponse, RootResponse

router = APIRouter(tags=["Core"])


@router.get(
    "/",
    response_model=RootResponse,
    summary="Service identity",
    description="Returns the service name and its current operational status.",
)
async def root() -> RootResponse:
    return RootResponse(service="Intervexa API", status="running")


@router.get(
    "/health",
    response_model=HealthResponse,
    summary="Health check",
    description="Lightweight liveness probe — returns 200 when the service is healthy.",
)
async def health_check() -> HealthResponse:
    return HealthResponse(status="healthy")

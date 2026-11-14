from fastapi import APIRouter, Depends, Request, Response, status
from prometheus_client import CONTENT_TYPE_LATEST, REGISTRY, generate_latest
from prometheus_client.openmetrics.exposition import (
    CONTENT_TYPE_LATEST as OPENMETRICS_CONTENT_TYPE_LATEST,
    generate_latest as openmetrics_generate_latest,
)

from app.database import check_database_connection
from app.dependencies import get_queue_service
from app.schemas.health import HealthResponse, ReadinessResponse
from app.services.queue_service import QueueProducerProtocol

router = APIRouter(tags=["probes"])


@router.get("/healthz", response_model=HealthResponse, status_code=status.HTTP_200_OK)
async def health_check() -> HealthResponse:
    return HealthResponse(status="ok")


@router.get("/readyz", response_model=ReadinessResponse)
async def readiness_check(
    response: Response,
    queue_service: QueueProducerProtocol = Depends(get_queue_service),
) -> ReadinessResponse:
    db_healthy = await check_database_connection()
    redis_healthy = await queue_service.check_health()

    db_status = "connected" if db_healthy else "unreachable"
    redis_status = "connected" if redis_healthy else "unreachable"

    if db_healthy and redis_healthy:
        response.status_code = status.HTTP_200_OK
        return ReadinessResponse(
            status="ready",
            database=db_status,
            redis=redis_status,
        )

    response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
    return ReadinessResponse(
        status="unavailable",
        database=db_status,
        redis=redis_status,
    )


@router.get("/metrics")
async def metrics(request: Request) -> Response:
    accept_header = request.headers.get("accept", "")
    if "application/openmetrics-text" in accept_header:
        return Response(
            content=openmetrics_generate_latest(REGISTRY),
            media_type=OPENMETRICS_CONTENT_TYPE_LATEST,
        )
    return Response(content=generate_latest(), media_type=CONTENT_TYPE_LATEST)

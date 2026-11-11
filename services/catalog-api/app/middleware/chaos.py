import asyncio
import random
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse, Response

from app.config import settings


class ChaosMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next) -> Response:
        if request.url.path in {"/healthz", "/readyz", "/metrics"}:
            return await call_next(request)

        if settings.CHAOS_ERROR_RATE > 0 and random.random() < settings.CHAOS_ERROR_RATE:
            return JSONResponse(
                status_code=500,
                content={"error": "Chaos fault injected: artificial 500 error"},
            )

        if settings.CHAOS_LATENCY_MS > 0:
            await asyncio.sleep(settings.CHAOS_LATENCY_MS / 1000.0)

        return await call_next(request)

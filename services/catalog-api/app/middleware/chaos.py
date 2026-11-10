import asyncio
import os
import random
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse, Response


class ChaosMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next) -> Response:
        if request.url.path in {"/healthz", "/readyz", "/metrics"}:
            return await call_next(request)

        chaos_error_rate = float(os.getenv("CHAOS_ERROR_RATE", "0"))
        if chaos_error_rate > 0 and random.random() < chaos_error_rate:
            return JSONResponse(
                status_code=500,
                content={"error": "Chaos fault injected: artificial 500 error"},
            )

        chaos_latency_ms = int(os.getenv("CHAOS_LATENCY_MS", "0"))
        if chaos_latency_ms > 0:
            await asyncio.sleep(chaos_latency_ms / 1000.0)

        return await call_next(request)

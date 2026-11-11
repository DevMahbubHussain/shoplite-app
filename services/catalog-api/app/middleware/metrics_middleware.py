import time
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

from app.observability.metrics import (
    HTTP_REQUEST_DURATION_SECONDS,
    HTTP_REQUESTS_TOTAL,
)


class MetricsMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next) -> Response:
        start_time = time.perf_counter()
        status_code = 500
        route_path = request.url.path

        try:
            response = await call_next(request)
            status_code = response.status_code
            return response
        finally:
            # Starlette stores the matched route in the scope during routing
            route = request.scope.get("route")
            if route is not None:
                route_path = route.path

            duration = time.perf_counter() - start_time
            HTTP_REQUESTS_TOTAL.labels(
                method=request.method,
                route=route_path,
                status=str(status_code),
            ).inc()

            HTTP_REQUEST_DURATION_SECONDS.labels(
                method=request.method,
                route=route_path,
            ).observe(duration)

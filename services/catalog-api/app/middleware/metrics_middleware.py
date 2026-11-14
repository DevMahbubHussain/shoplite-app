import time
from opentelemetry import trace
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

            span = trace.get_current_span()
            span_ctx = span.get_span_context() if span else None
            exemplar = None
            if span_ctx and span_ctx.is_valid:
                exemplar = {"TraceID": trace.format_trace_id(span_ctx.trace_id)}

            if exemplar:
                HTTP_REQUEST_DURATION_SECONDS.labels(
                    method=request.method,
                    route=route_path,
                ).observe(duration, exemplar=exemplar)
            else:
                HTTP_REQUEST_DURATION_SECONDS.labels(
                    method=request.method,
                    route=route_path,
                ).observe(duration)

import asyncio
import json
import os
import time
from typing import Any
from opentelemetry import trace

from app.config import worker_settings
from app.database import simulate_slow_query, update_order_status
from app.logging import logger
from app.metrics import ORDER_PROCESSING_SECONDS, ORDERS_PROCESSED_TOTAL
from app.tracing import extract_trace_context

tracer = trace.get_tracer("order-worker")
_leak_buffer: list[bytes] = []


class OrderProcessor:
    def __init__(self) -> None:
        pass

    async def process_payload(self, raw_payload: str) -> bool:
        start_time = time.perf_counter()
        order_id: int | None = None
        trace_id_str = ""

        try:
            payload: dict[str, Any] = json.loads(raw_payload)
            order_id = int(payload.get("order_id", 0))
            traceparent = str(payload.get("traceparent", ""))

            carrier = {"traceparent": traceparent} if traceparent else {}
            ctx = extract_trace_context(carrier)

            with tracer.start_as_current_span("worker_process_order", context=ctx) as span:
                span_ctx = span.get_span_context()
                if span_ctx and span_ctx.is_valid:
                    trace_id_str = trace.format_trace_id(span_ctx.trace_id)

                # Check Chaos: Memory Leak simulation
                chaos_leak = os.getenv("CHAOS_MEMORY_LEAK", "false").lower() in ("true", "1")
                if chaos_leak or worker_settings.CHAOS_MEMORY_LEAK:
                    _leak_buffer.append(b"M" * 2 * 1024 * 1024)
                    logger.warning("Chaos memory leak injected: allocated 2MB", extra={"order_id": order_id})

                # Check Chaos: Slow DB simulation
                chaos_slow = os.getenv("CHAOS_SLOW_DB", "false").lower() in ("true", "1")
                if chaos_slow or worker_settings.CHAOS_SLOW_DB:
                    logger.warning("Chaos slow DB injected: sleeping 2s", extra={"order_id": order_id})
                    try:
                        await simulate_slow_query()
                    except Exception:
                        await asyncio.sleep(2.0)

                # Simulate business logic processing delay (1-2s)
                delay = worker_settings.PROCESSING_DELAY_SECONDS
                if delay > 0:
                    await asyncio.sleep(delay)

                # Update database status to COMPLETED
                updated = await update_order_status(order_id, "COMPLETED")
                if not updated:
                    logger.warning(
                        f"Order {order_id} not updated in database, record might not exist yet",
                        extra={"order_id": order_id, "trace_id": trace_id_str},
                    )

                duration = time.perf_counter() - start_time
                ORDER_PROCESSING_SECONDS.observe(duration)
                ORDERS_PROCESSED_TOTAL.labels(result="success").inc()

                logger.info(
                    "Order processed successfully",
                    extra={
                        "order_id": order_id,
                        "trace_id": trace_id_str,
                        "duration_ms": round(duration * 1000, 2),
                    },
                )
                return True

        except Exception as exc:
            duration = time.perf_counter() - start_time
            ORDERS_PROCESSED_TOTAL.labels(result="failed").inc()
            logger.error(
                f"Failed to process order payload: {exc}",
                extra={"order_id": order_id, "trace_id": trace_id_str},
                exc_info=True,
            )
            return False

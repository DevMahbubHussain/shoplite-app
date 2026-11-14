import asyncio
import json
import random
import time
from enum import Enum
from typing import Any
from opentelemetry import trace

from worker.config import worker_settings
from worker.database import simulate_slow_query, update_order_status
from worker.logging import logger
from worker.metrics import ORDER_PROCESSING_SECONDS, ORDERS_PROCESSED_TOTAL
from worker.tracing import extract_trace_context

tracer = trace.get_tracer("order-worker")
_leak_buffer: list[bytes] = []


class ProcessingResult(str, Enum):
    SUCCESS = "SUCCESS"
    RETRY = "RETRY"
    DISCARD = "DISCARD"


def _parse_payload(raw_payload: str) -> tuple[dict[str, Any], int] | None:
    try:
        payload: dict[str, Any] = json.loads(raw_payload)
        order_id = int(payload["order_id"])
        return payload, order_id
    except (json.JSONDecodeError, KeyError, TypeError, ValueError):
        return None


class OrderProcessor:
    async def process_payload(self, raw_payload: str) -> ProcessingResult:
        start_time = time.perf_counter()
        parsed = _parse_payload(raw_payload)

        if parsed is None:
            logger.error("Discarding malformed order payload (unparseable or missing order_id)")
            ORDER_PROCESSING_SECONDS.observe(time.perf_counter() - start_time)
            ORDERS_PROCESSED_TOTAL.labels(result="failed").inc()
            return ProcessingResult.DISCARD

        payload, order_id = parsed
        traceparent = str(payload.get("traceparent", ""))
        carrier = {"traceparent": traceparent} if traceparent else {}
        ctx = extract_trace_context(carrier)

        with tracer.start_as_current_span("worker_process_order", context=ctx) as span:
            span_ctx = span.get_span_context()
            trace_id_str = (
                trace.format_trace_id(span_ctx.trace_id) if span_ctx and span_ctx.is_valid else ""
            )

            try:
                result = await self._fulfill_order(order_id)
            except Exception as exc:
                # Transient infrastructure failure: payload is kept for retry
                self._record_attempt(start_time, result="failed", trace_id=trace_id_str)
                logger.error(
                    f"Transient failure processing order {order_id}: {exc}",
                    extra={"order_id": order_id, "trace_id": trace_id_str},
                    exc_info=True,
                )
                return ProcessingResult.RETRY

            self._record_attempt(
                start_time, result="success" if result else "failed", trace_id=trace_id_str
            )
            return ProcessingResult.SUCCESS if result else ProcessingResult.DISCARD

    async def _fulfill_order(self, order_id: int) -> bool:
        await self._apply_chaos(order_id)

        delay = random.uniform(
            worker_settings.PROCESSING_DELAY_MIN_SECONDS,
            worker_settings.PROCESSING_DELAY_MAX_SECONDS,
        )
        if delay > 0:
            await asyncio.sleep(delay)

        if not await update_order_status(order_id, "PROCESSING"):
            logger.warning(
                f"Order {order_id} not found in database; discarding payload",
                extra={"order_id": order_id},
            )
            return False

        if not await update_order_status(order_id, "COMPLETED"):
            logger.warning(
                f"Order {order_id} disappeared before completion; discarding payload",
                extra={"order_id": order_id},
            )
            return False

        logger.info(
            "Order processed successfully",
            extra={"order_id": order_id, "status": "COMPLETED"},
        )
        return True

    async def _apply_chaos(self, order_id: int) -> None:
        if worker_settings.CHAOS_MEMORY_LEAK:
            _leak_buffer.append(b"M" * 2 * 1024 * 1024)
            logger.warning("Chaos memory leak injected: allocated 2MB", extra={"order_id": order_id})

        if worker_settings.CHAOS_SLOW_DB:
            logger.warning("Chaos slow DB injected: sleeping 2s", extra={"order_id": order_id})
            try:
                await simulate_slow_query()
            except Exception:
                await asyncio.sleep(2.0)

    def _record_attempt(self, start_time: float, result: str, trace_id: str = "") -> None:
        duration = time.perf_counter() - start_time
        if trace_id:
            ORDER_PROCESSING_SECONDS.observe(duration, exemplar={"TraceID": trace_id})
        else:
            ORDER_PROCESSING_SECONDS.observe(duration)
        ORDERS_PROCESSED_TOTAL.labels(result=result).inc()

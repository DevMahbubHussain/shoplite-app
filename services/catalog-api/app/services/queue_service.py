import json
import time
from typing import Any, Protocol
import redis.asyncio as redis

from app.config import settings
from app.observability.logging import logger
from app.observability.metrics import ORDER_QUEUE_DEPTH
from app.observability.tracing import inject_trace_context


class QueueProducerProtocol(Protocol):
    async def push_order(self, order_id: int, product_id: int, quantity: int) -> None: ...
    async def get_queue_depth(self) -> int: ...
    async def check_health(self) -> bool: ...


class RedisQueueService:
    def __init__(self, client: redis.Redis | None = None) -> None:
        self.client = client or redis.Redis(
            host=settings.REDIS_HOST,
            port=settings.REDIS_PORT,
            db=settings.REDIS_DB,
            decode_responses=True,
        )

    async def push_order(self, order_id: int, product_id: int, quantity: int) -> None:
        carrier: dict[str, str] = {}
        inject_trace_context(carrier)

        payload: dict[str, Any] = {
            "order_id": order_id,
            "product_id": product_id,
            "quantity": quantity,
            "traceparent": carrier.get("traceparent", ""),
            "timestamp": time.time(),
        }

        raw_payload = json.dumps(payload)
        await self.client.lpush(settings.REDIS_PENDING_QUEUE, raw_payload)
        depth = await self.client.llen(settings.REDIS_PENDING_QUEUE)
        ORDER_QUEUE_DEPTH.set(depth)

        logger.info(
            f"Enqueued order {order_id} to {settings.REDIS_PENDING_QUEUE}",
            extra={"order_id": order_id, "queue_depth": depth},
        )

    async def get_queue_depth(self) -> int:
        try:
            depth = await self.client.llen(settings.REDIS_PENDING_QUEUE)
            ORDER_QUEUE_DEPTH.set(depth)
            return depth
        except Exception:
            return 0

    async def check_health(self) -> bool:
        try:
            return bool(await self.client.ping())
        except Exception:
            return False

    async def close(self) -> None:
        await self.client.aclose()

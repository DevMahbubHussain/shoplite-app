import asyncio
from typing import Any
import redis.asyncio as redis

from worker.config import worker_settings
from worker.logging import logger
from worker.metrics import ORDER_QUEUE_DEPTH
from worker.processor import OrderProcessor, ProcessingResult


class QueueConsumer:
    def __init__(
        self,
        processor: OrderProcessor | None = None,
        redis_client: Any = None,
    ) -> None:
        self.processor = processor or OrderProcessor()
        self.redis = redis_client
        self.is_running = True
        self.in_flight = False
        self._stop_lock = asyncio.Lock()

    async def init_redis(self) -> None:
        if self.redis is None:
            self.redis = redis.Redis(
                host=worker_settings.REDIS_HOST,
                port=worker_settings.REDIS_PORT,
                db=worker_settings.REDIS_DB,
                decode_responses=True,
            )

    async def recovery_sweep(self) -> int:
        processing_key = worker_settings.REDIS_PROCESSING_QUEUE
        pending_key = worker_settings.REDIS_PENDING_QUEUE

        recovered = 0
        while True:
            # Atomically move unhandled item back to pending
            item = await self.redis.rpoplpush(processing_key, pending_key)
            if not item:
                break
            recovered += 1

        if recovered > 0:
            logger.info(
                f"Startup recovery sweep: restored {recovered} unhandled orders to {pending_key}",
                extra={"recovered_count": recovered},
            )
        return recovered

    async def run(self) -> None:
        await self.init_redis()
        await self.recovery_sweep()

        logger.info(
            f"Worker consumer active, listening on {worker_settings.REDIS_PENDING_QUEUE} -> {worker_settings.REDIS_PROCESSING_QUEUE}"
        )

        while self.is_running:
            try:
                depth = await self.redis.llen(worker_settings.REDIS_PENDING_QUEUE)
                ORDER_QUEUE_DEPTH.set(depth)

                # Atomically double-buffer from pending to processing
                payload = await self.redis.brpoplpush(
                    worker_settings.REDIS_PENDING_QUEUE,
                    worker_settings.REDIS_PROCESSING_QUEUE,
                    timeout=worker_settings.REDIS_POP_TIMEOUT,
                )

                if payload:
                    self.in_flight = True
                    try:
                        await self._handle_payload(payload)
                    finally:
                        self.in_flight = False

            except asyncio.CancelledError:
                logger.info("Worker loop cancelled during shutdown")
                break
            except Exception as exc:
                logger.error(f"Error in worker consumer loop: {exc}", exc_info=True)
                await asyncio.sleep(1.0)

        logger.info("Worker consumer loop exited cleanly")

    async def _handle_payload(self, payload: str) -> None:
        result = await self.processor.process_payload(payload)

        if result is ProcessingResult.RETRY:
            # LPUSH first so the payload is never lost, then deduplicate processing
            await self.redis.lpush(worker_settings.REDIS_PENDING_QUEUE, payload)
            await self.redis.lrem(worker_settings.REDIS_PROCESSING_QUEUE, 1, payload)
            await asyncio.sleep(worker_settings.RETRY_DELAY_SECONDS)
            logger.info("Transient failure: payload requeued for retry", extra={"result": "RETRY"})
            return

        await self.redis.lrem(worker_settings.REDIS_PROCESSING_QUEUE, 1, payload)

    async def stop(self) -> None:
        # Idempotent: signal handler and finalizer may both request shutdown
        async with self._stop_lock:
            self.is_running = False
            while self.in_flight:
                logger.info("Waiting for in-flight order commit before shutdown...")
                await asyncio.sleep(0.1)

            client, self.redis = self.redis, None
            if client:
                await client.aclose()
            logger.info("Worker stopped successfully")

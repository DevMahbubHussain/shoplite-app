import asyncio
import json
from unittest.mock import AsyncMock, patch
import pytest

from app.consumer import QueueConsumer
from app.processor import OrderProcessor


class MockRedis:
    def __init__(self) -> None:
        self.pending: list[str] = []
        self.processing: list[str] = []

    async def rpoplpush(self, src: str, dst: str) -> str | None:
        if src == "orders:processing" and self.processing:
            item = self.processing.pop(0)
            self.pending.append(item)
            return item
        return None

    async def brpoplpush(self, src: str, dst: str, timeout: int = 1) -> str | None:
        if self.pending:
            item = self.pending.pop(0)
            self.processing.append(item)
            return item
        await asyncio.sleep(0.02)
        return None

    async def llen(self, key: str) -> int:
        return len(self.pending) if key == "orders:pending" else len(self.processing)

    async def lrem(self, key: str, count: int, element: str) -> int:
        if element in self.processing:
            self.processing.remove(element)
            return 1
        return 0

    async def aclose(self) -> None:
        pass


@pytest.mark.asyncio
async def test_recovery_sweep_restores_unhandled_orders():
    mock_redis = MockRedis()
    mock_redis.processing = ['{"order_id": 101}', '{"order_id": 102}']

    consumer = QueueConsumer(redis_client=mock_redis)
    recovered = await consumer.recovery_sweep()

    assert recovered == 2
    assert len(mock_redis.processing) == 0
    assert len(mock_redis.pending) == 2
    assert mock_redis.pending == ['{"order_id": 101}', '{"order_id": 102}']


@pytest.mark.asyncio
async def test_order_processor_success():
    payload = json.dumps({
        "order_id": 101,
        "product_id": 1,
        "quantity": 2,
        "traceparent": "00-4bf92f3577b34da6a3ce929d0e0e4736-00f067aa0ba902b7-01",
        "timestamp": 1700000000.0,
    })

    processor = OrderProcessor()
    with patch("app.processor.update_order_status", new_callable=AsyncMock) as mock_update, \
         patch("app.config.worker_settings.PROCESSING_DELAY_SECONDS", 0):
        mock_update.return_value = True
        success = await processor.process_payload(payload)

        assert success is True
        mock_update.assert_awaited_once_with(101, "COMPLETED")


@pytest.mark.asyncio
async def test_order_processor_invalid_json():
    processor = OrderProcessor()
    success = await processor.process_payload("invalid json payload")
    assert success is False


@pytest.mark.asyncio
async def test_consumer_loop_single_order_lifecycle():
    mock_redis = MockRedis()
    test_payload = json.dumps({"order_id": 55, "product_id": 2, "quantity": 1})
    mock_redis.pending.append(test_payload)

    processor = OrderProcessor()
    with patch("app.processor.update_order_status", new_callable=AsyncMock) as mock_update, \
         patch("app.config.worker_settings.PROCESSING_DELAY_SECONDS", 0):
        mock_update.return_value = True

        consumer = QueueConsumer(processor=processor, redis_client=mock_redis)

        # Run consumer in task and stop immediately after 1 iteration
        async def run_and_stop():
            task = asyncio.create_task(consumer.run())
            while len(mock_redis.processing) > 0 or len(mock_redis.pending) > 0:
                await asyncio.sleep(0.01)
            await consumer.stop()
            await task

        await run_and_stop()

        assert len(mock_redis.processing) == 0
        assert len(mock_redis.pending) == 0
        mock_update.assert_awaited_once_with(55, "COMPLETED")

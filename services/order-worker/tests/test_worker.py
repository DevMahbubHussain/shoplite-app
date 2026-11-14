import asyncio
import json
from unittest.mock import AsyncMock, patch
import pytest

from worker.config import worker_settings
from worker.consumer import QueueConsumer
from worker.processor import OrderProcessor, ProcessingResult


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
            item = self.pending.pop()
            self.processing.append(item)
            return item
        await asyncio.sleep(0.02)
        return None

    async def lpush(self, key: str, value: str) -> int:
        if key == "orders:pending":
            self.pending.insert(0, value)
            return 1
        return 0

    async def llen(self, key: str) -> int:
        return len(self.pending) if key == "orders:pending" else len(self.processing)

    async def lrem(self, key: str, count: int, element: str) -> int:
        if element in self.processing:
            self.processing.remove(element)
            return 1
        return 0

    async def aclose(self) -> None:
        pass


def zero_delay():
    return (
        patch.object(worker_settings, "PROCESSING_DELAY_MIN_SECONDS", 0),
        patch.object(worker_settings, "PROCESSING_DELAY_MAX_SECONDS", 0),
    )


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
async def test_order_processor_transitions_to_processing_then_completed():
    payload = json.dumps({
        "order_id": 101,
        "product_id": 1,
        "quantity": 2,
        "traceparent": "00-4bf92f3577b34da6a3ce929d0e0e4736-00f067aa0ba902b7-01",
        "timestamp": 1700000000.0,
    })

    processor = OrderProcessor()
    patches = zero_delay() + (
        patch("worker.processor.update_order_status", new_callable=AsyncMock),
    )
    with patches[0], patches[1], patches[2] as mock_update:
        mock_update.return_value = True
        result = await processor.process_payload(payload)

        assert result is ProcessingResult.SUCCESS
        assert mock_update.await_count == 2
        assert mock_update.await_args_list[0].args == (101, "PROCESSING")
        assert mock_update.await_args_list[-1].args == (101, "COMPLETED")


@pytest.mark.asyncio
async def test_order_processor_invalid_json_discards_without_db_call():
    processor = OrderProcessor()
    with patch("worker.processor.update_order_status", new_callable=AsyncMock) as mock_update:
        result = await processor.process_payload("invalid json payload")

    assert result is ProcessingResult.DISCARD
    mock_update.assert_not_awaited()


@pytest.mark.asyncio
async def test_order_processor_missing_row_discards_payload():
    processor = OrderProcessor()
    payload = json.dumps({"order_id": 999})
    patches = zero_delay() + (
        patch("worker.processor.update_order_status", new_callable=AsyncMock),
    )
    with patches[0], patches[1], patches[2] as mock_update:
        mock_update.return_value = False
        result = await processor.process_payload(payload)

    assert result is ProcessingResult.DISCARD
    mock_update.assert_awaited_once_with(999, "PROCESSING")


@pytest.mark.asyncio
async def test_order_processor_transient_db_failure_requests_retry():
    processor = OrderProcessor()
    payload = json.dumps({"order_id": 42})
    patches = zero_delay() + (
        patch("worker.processor.update_order_status", new_callable=AsyncMock),
    )
    with patches[0], patches[1], patches[2] as mock_update:
        mock_update.side_effect = Exception("db connection lost")
        result = await processor.process_payload(payload)

    assert result is ProcessingResult.RETRY


@pytest.mark.asyncio
async def test_consumer_requeues_payload_on_transient_failure():
    class RetryStub:
        async def process_payload(self, raw_payload: str) -> ProcessingResult:
            return ProcessingResult.RETRY

    mock_redis = MockRedis()
    payload = json.dumps({"order_id": 5})
    mock_redis.pending.append(payload)

    consumer = QueueConsumer(processor=RetryStub(), redis_client=mock_redis)
    with patch.object(worker_settings, "RETRY_DELAY_SECONDS", 0):
        run_task = asyncio.create_task(consumer.run())
        picked_up = False
        for _ in range(400):
            if mock_redis.processing:
                picked_up = True
            if picked_up and not mock_redis.processing and payload in mock_redis.pending:
                break
            await asyncio.sleep(0.01)
        await consumer.stop()
        await run_task

    assert payload in mock_redis.pending
    assert mock_redis.processing == []


@pytest.mark.asyncio
async def test_graceful_shutdown_completes_inflight_order():
    mock_redis = MockRedis()
    payload = json.dumps({"order_id": 77, "product_id": 1, "quantity": 1})
    mock_redis.pending.append(payload)

    processor = OrderProcessor()
    patches = (
        patch.object(worker_settings, "PROCESSING_DELAY_MIN_SECONDS", 0.3),
        patch.object(worker_settings, "PROCESSING_DELAY_MAX_SECONDS", 0.3),
        patch("worker.processor.update_order_status", new_callable=AsyncMock),
    )
    with patches[0], patches[1], patches[2] as mock_update:
        mock_update.return_value = True
        consumer = QueueConsumer(processor=processor, redis_client=mock_redis)

        run_task = asyncio.create_task(consumer.run())
        await asyncio.sleep(0.05)
        await consumer.stop()
        await run_task

        assert mock_update.await_count == 2
        assert mock_update.await_args_list[-1].args == (77, "COMPLETED")
        assert mock_redis.processing == []


@pytest.mark.asyncio
async def test_chaos_slow_db_flag_activates():
    processor = OrderProcessor()
    payload = json.dumps({"order_id": 8})
    patches = zero_delay() + (
        patch.object(worker_settings, "CHAOS_SLOW_DB", True),
        patch("worker.processor.simulate_slow_query", new_callable=AsyncMock),
        patch("worker.processor.update_order_status", new_callable=AsyncMock),
    )
    with patches[0], patches[1], patches[2], patches[3] as mock_slow, patches[4] as mock_update:
        mock_update.return_value = True
        result = await processor.process_payload(payload)

    assert result is ProcessingResult.SUCCESS
    mock_slow.assert_awaited_once()


@pytest.mark.asyncio
async def test_chaos_memory_leak_flag_activates():
    processor = OrderProcessor()
    payload = json.dumps({"order_id": 9})
    patches = zero_delay() + (
        patch.object(worker_settings, "CHAOS_MEMORY_LEAK", True),
        patch("worker.processor._leak_buffer", []),
        patch("worker.processor.update_order_status", new_callable=AsyncMock),
    )
    with patches[0], patches[1], patches[2], patches[3] as leak_buffer, patches[4] as mock_update:
        mock_update.return_value = True
        result = await processor.process_payload(payload)

    assert result is ProcessingResult.SUCCESS
    assert len(leak_buffer) == 1


@pytest.mark.asyncio
async def test_consumer_loop_single_order_lifecycle():
    mock_redis = MockRedis()
    test_payload = json.dumps({"order_id": 55, "product_id": 2, "quantity": 1})
    mock_redis.pending.append(test_payload)

    processor = OrderProcessor()
    patches = zero_delay() + (
        patch("worker.processor.update_order_status", new_callable=AsyncMock),
    )
    with patches[0], patches[1], patches[2] as mock_update:
        mock_update.return_value = True

        consumer = QueueConsumer(processor=processor, redis_client=mock_redis)

        async def run_and_stop():
            task = asyncio.create_task(consumer.run())
            for _ in range(200):
                if not mock_redis.pending and not mock_redis.processing:
                    break
                await asyncio.sleep(0.01)
            await consumer.stop()
            await task

        await run_and_stop()

        assert len(mock_redis.processing) == 0
        assert len(mock_redis.pending) == 0
        assert mock_update.await_count == 2
        assert mock_update.await_args_list[-1].args == (55, "COMPLETED")


@pytest.mark.asyncio
async def test_order_processor_with_traceparent():
    processor = OrderProcessor()
    payload = json.dumps({
        "order_id": 99,
        "traceparent": "00-4bf92f3577b34da6a3ce929d0e0e4736-00f067aa0ba902b7-01",
    })
    patches = zero_delay() + (
        patch("worker.processor.update_order_status", new_callable=AsyncMock),
    )
    with patches[0], patches[1], patches[2] as mock_update:
        mock_update.return_value = True
        result = await processor.process_payload(payload)

    assert result is ProcessingResult.SUCCESS
    assert mock_update.await_count == 2

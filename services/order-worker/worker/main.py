import asyncio
import signal
import sys

from opentelemetry.instrumentation.redis import RedisInstrumentor

from worker.config import worker_settings
from worker.consumer import QueueConsumer
from worker.logging import logger
from worker.metrics import start_metrics_server
from worker.tracing import init_worker_tracer

_pending_tasks: set[asyncio.Task] = set()


def main() -> None:
    logger.info(f"Starting {worker_settings.SERVICE_NAME} daemon")

    start_metrics_server(worker_settings.METRICS_PORT)
    logger.info(f"Metrics server listening on port {worker_settings.METRICS_PORT}")

    init_worker_tracer(
        service_name=worker_settings.SERVICE_NAME,
        endpoint=worker_settings.OTEL_EXPORTER_OTLP_ENDPOINT,
        enabled=worker_settings.OTEL_ENABLED,
    )
    RedisInstrumentor().instrument()

    consumer = QueueConsumer()
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)

    def request_shutdown() -> None:
        task = loop.create_task(consumer.stop())
        _pending_tasks.add(task)
        task.add_done_callback(_pending_tasks.discard)

    if sys.platform != "win32":
        loop.add_signal_handler(signal.SIGTERM, request_shutdown)
        loop.add_signal_handler(signal.SIGINT, request_shutdown)
    else:
        signal.signal(signal.SIGINT, lambda sig, frame: request_shutdown())
        signal.signal(signal.SIGTERM, lambda sig, frame: request_shutdown())

    try:
        loop.run_until_complete(consumer.run())
    finally:
        loop.run_until_complete(consumer.stop())
        loop.close()
        logger.info("Worker shutdown sequence finalized")


if __name__ == "__main__":
    main()

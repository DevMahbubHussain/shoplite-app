import asyncio
import signal
import sys

from app.config import worker_settings
from app.consumer import QueueConsumer
from app.logging import logger
from app.metrics import start_metrics_server
from app.tracing import init_worker_tracer


def main() -> None:
    logger.info(f"Starting {worker_settings.SERVICE_NAME} daemon")

    # Start Prometheus exposition server
    start_metrics_server(worker_settings.METRICS_PORT)
    logger.info(f"Metrics server listening on port {worker_settings.METRICS_PORT}")

    if worker_settings.OTEL_ENABLED:
        init_worker_tracer(
            service_name=worker_settings.SERVICE_NAME,
            endpoint=worker_settings.OTEL_EXPORTER_OTLP_ENDPOINT,
            enabled=True,
        )

    consumer = QueueConsumer()
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)

    def handle_shutdown_signal(sig, frame):
        logger.info(f"Received shutdown signal {sig}, initiating graceful termination")
        loop.create_task(consumer.stop())

    if sys.platform != "win32":
        loop.add_signal_handler(signal.SIGTERM, lambda: asyncio.create_task(consumer.stop()))
        loop.add_signal_handler(signal.SIGINT, lambda: asyncio.create_task(consumer.stop()))
    else:
        signal.signal(signal.SIGINT, handle_shutdown_signal)
        signal.signal(signal.SIGTERM, handle_shutdown_signal)

    try:
        loop.run_until_complete(consumer.run())
    finally:
        loop.run_until_complete(consumer.stop())
        loop.close()
        logger.info("Worker shutdown sequence finalized")


if __name__ == "__main__":
    main()

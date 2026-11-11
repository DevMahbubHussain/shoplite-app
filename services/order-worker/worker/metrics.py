from prometheus_client import CollectorRegistry, Counter, Gauge, Histogram, start_http_server

from worker.logging import logger

# Dedicated registry: order_queue_depth also exists in catalog-api when both
# modules load into one process (unit tests)
WORKER_REGISTRY = CollectorRegistry(auto_describe=True)

ORDERS_PROCESSED_TOTAL = Counter(
    "orders_processed_total",
    "Total orders processed by background worker",
    ["result"],
    registry=WORKER_REGISTRY,
)

ORDER_PROCESSING_SECONDS = Histogram(
    "order_processing_seconds",
    "Time spent processing individual orders in seconds",
    buckets=(0.1, 0.25, 0.5, 1.0, 1.5, 2.0, 3.0, 5.0, 10.0),
    registry=WORKER_REGISTRY,
)

ORDER_QUEUE_DEPTH = Gauge(
    "order_queue_depth",
    "Current number of pending orders in Redis queue",
    registry=WORKER_REGISTRY,
)


def start_metrics_server(port: int = 9102) -> None:
    try:
        start_http_server(port, registry=WORKER_REGISTRY)
    except Exception as exc:
        logger.warning(f"Metrics server failed to bind port {port}: {exc}")

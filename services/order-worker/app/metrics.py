from prometheus_client import Counter, Gauge, Histogram, start_http_server

ORDERS_PROCESSED_TOTAL = Counter(
    "orders_processed_total",
    "Total orders processed by background worker",
    ["result"],
)

ORDER_PROCESSING_SECONDS = Histogram(
    "order_processing_seconds",
    "Time spent processing individual orders in seconds",
    buckets=(0.1, 0.25, 0.5, 1.0, 1.5, 2.0, 3.0, 5.0, 10.0),
)

ORDER_QUEUE_DEPTH = Gauge(
    "order_queue_depth",
    "Current number of pending orders in Redis queue",
)


def start_metrics_server(port: int = 9102) -> None:
    try:
        start_http_server(port)
    except Exception:
        pass

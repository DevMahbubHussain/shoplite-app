from prometheus_client import Counter, Histogram, Gauge

HTTP_REQUESTS_TOTAL = Counter(
    "http_requests_total",
    "Total incoming HTTP requests",
    ["method", "route", "status"],
)

HTTP_REQUEST_DURATION_SECONDS = Histogram(
    "http_request_duration_seconds",
    "HTTP request latency distribution in seconds",
    ["method", "route"],
    buckets=(0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0),
)

ORDERS_CREATED_TOTAL = Counter(
    "orders_created_total",
    "Total orders created successfully",
)

ORDER_QUEUE_DEPTH = Gauge(
    "order_queue_depth",
    "Current number of pending orders in Redis queue",
)

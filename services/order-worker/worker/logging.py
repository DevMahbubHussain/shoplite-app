import json
import logging
import sys
from datetime import datetime, timezone
from typing import Any
from opentelemetry import trace


class StructuredJSONFormatter(logging.Formatter):
    def __init__(self, service_name: str = "order-worker") -> None:
        super().__init__()
        self.service_name = service_name

    def format(self, record: logging.LogRecord) -> str:
        span = trace.get_current_span()
        span_context = span.get_span_context() if span else None
        trace_id = ""
        if span_context and span_context.is_valid:
            trace_id = trace.format_trace_id(span_context.trace_id)

        log_data: dict[str, Any] = {
            "timestamp": datetime.now(timezone.utc).isoformat(timespec="milliseconds").replace("+00:00", "Z"),
            "level": record.levelname,
            "service": self.service_name,
            "message": record.getMessage(),
            "trace_id": getattr(record, "trace_id", None) or trace_id,
        }

        for key, value in record.__dict__.items():
            if key not in {
                "args", "asctime", "created", "exc_info", "exc_text", "filename",
                "funcName", "id", "levelname", "levelno", "lineno", "module",
                "msecs", "message", "msg", "name", "pathname", "process",
                "processName", "relativeCreated", "stack_info", "thread",
                "threadName", "trace_id"
            }:
                log_data[key] = value

        if record.exc_info:
            log_data["exception"] = self.formatException(record.exc_info)

        return json.dumps(log_data)


def setup_logger(service_name: str = "order-worker", log_level: str = "INFO") -> logging.Logger:
    logger = logging.getLogger(service_name)
    logger.setLevel(getattr(logging, log_level.upper(), logging.INFO))
    logger.handlers.clear()

    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(StructuredJSONFormatter(service_name=service_name))
    logger.addHandler(handler)
    logger.propagate = False
    return logger


logger = setup_logger()

# Stage 1: Build virtual environment
FROM python:3.11-alpine AS builder

WORKDIR /build

RUN apk add --no-cache gcc musl-dev libffi-dev binutils

COPY requirements.txt .
RUN python -m venv /opt/venv && \
    /opt/venv/bin/pip install --no-cache-dir --upgrade pip && \
    /opt/venv/bin/pip install --no-cache-dir -r requirements.txt && \
    find /opt/venv -type f -name "*.so*" -exec strip --strip-unneeded {} + 2>/dev/null || true && \
    rm -rf /opt/venv/lib/python3.11/site-packages/pip* \
           /opt/venv/lib/python3.11/site-packages/setuptools* \
           /opt/venv/lib/python3.11/site-packages/pkg_resources && \
    find /opt/venv -type d -name "__pycache__" -prune -exec rm -rf {} + 2>/dev/null || true && \
    find /opt/venv -type d -name "tests" -prune -exec rm -rf {} + 2>/dev/null || true && \
    find /opt/venv -type f -name "*.pyc" -delete

# Stage 2: Runtime image
FROM python:3.11-alpine AS runner

WORKDIR /app

RUN apk add --no-cache curl && \
    addgroup -g 10001 -S appuser && \
    adduser -u 10001 -S appuser -G appuser

COPY --from=builder /opt/venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH" \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

COPY --chown=appuser:appuser worker /app/worker

USER 10001

EXPOSE 9102

HEALTHCHECK --interval=15s --timeout=5s --retries=3 \
  CMD curl -f http://localhost:9102/metrics || exit 1

CMD ["python", "-m", "worker.main"]

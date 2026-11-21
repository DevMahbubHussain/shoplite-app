# Phase 1: Local Compose Stack

## What

The complete five-service platform — `web`, `catalog-api`, `order-worker`, `postgres`, `redis` — built from source as multi-stage, non-root container images and orchestrated locally with Docker Compose, including a verified asynchronous order lifecycle.

## Why

The Compose stack is the fastest full-fidelity proof that the application contracts hold outside a developer's head: real database seeding, a real Redis queue, real background workers, and real HTTP contracts. Every later phase (Kubernetes, GitOps, chaos) depends on these same images and behaviors, so this gate must be green first.

## How

```bash
# Build all images (multi-stage, <150MB each) and start the stack
docker compose up -d --build

# Verify every service reports healthy
docker compose ps
```

Expected: five containers, all `healthy`. Postgres and Redis become healthy first; the API waits on them via `depends_on: condition: service_healthy`.

### Endpoint verification

| Check | Command | Expected |
| :--- | :--- | :--- |
| Liveness | `curl http://localhost:8000/healthz` | `{"status":"ok"}` |
| Readiness | `curl -i http://localhost:8000/readyz` | `HTTP/1.1 200` + `{"status":"ready","database":"connected","redis":"connected"}` |
| Catalog | `curl http://localhost:8000/products` | ≥10 seeded products (12 in this run) |
| Create order | see below | `201`, `status: PENDING` |
| Order lifecycle | poll `GET /orders/{id}` | `COMPLETED` + `completed_at` set |

```bash
# PowerShell-safe order creation (avoid curl quoting issues on Windows)
Invoke-RestMethod -Uri http://localhost:8000/orders -Method Post `
  -ContentType "application/json" -Body '{"product_id":1,"quantity":2}'
```

### Structured logs, metrics, runtime security

```bash
docker compose logs catalog-api --no-log-prefix   # single-line JSON with trace_id
curl http://localhost:8000/metrics | head -20     # Prometheus exposition
docker compose exec catalog-api id -u             # 10001 (non-root)
docker images --format "{{.Repository}}: {{.Size}}" | findstr shoplite
```

## Evidence

<img src="/screenshots/Q1-api-application/web-ui-catalog.png" alt="Web storefront" width="440">
<img src="/screenshots/Q1-api-application/health-readiness-probes.png" alt="Probes" width="440">
<img src="/screenshots/Q1-api-application/order-creation-201.png" alt="Order creation" width="440">
<img src="/screenshots/Q1-api-application/order-lifecycle-completed.png" alt="Order completed" width="440">

<img src="/screenshots/Q2-containerization/compose-services-healthy.png" alt="Compose healthy" width="440">
<img src="/screenshots/Q2-containerization/image-sizes-under-150mb.png" alt="Image sizes" width="440">
<img src="/screenshots/Q2-containerization/nonroot-uid-10001.png" alt="Non-root UID" width="440">
<img src="/screenshots/Q1-api-application/structured-json-logs.png" alt="JSON logs" width="440">
<img src="/screenshots/Q1-api-application/prometheus-metrics.png" alt="Metrics" width="440">

## Gate

All five containers `healthy`, order reaches `COMPLETED` with queues drained (`LLEN orders:pending` → 0), images under 150 MB, process UID `10001`.

Next: [Phase 2 — Linux Hardening](/deploy/02-linux-hardening).

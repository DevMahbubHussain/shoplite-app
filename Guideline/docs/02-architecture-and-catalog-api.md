# 2. Architecture & API Manual Testing (Question 1)

This section guides you through manually verifying the architecture topology, testing each of the 7 FastAPI endpoints, verifying the reliable queue pattern, and running the 29 unit tests.

---

## 2.1 Architecture Topology Review

The system follows a strict trust boundary architecture:

```
                  Internet
                     │
            ┌────────▼────────┐
            │   Public ALB    │ (AWS Application Load Balancer - 2 AZs)
            └────────┬────────┘
                     │ HTTP / HTTPS
            ┌────────▼────────────────────────────────────────┐
            │ Ingress Controller (ingress-nginx)              │
            └────────┬───────────────────────────────┬────────┘
                     │ path: /                       │ path: /api
         ┌───────────▼───────────┐       ┌───────────▼───────────┐
         │  web (Nginx + JS)     │       │  catalog-api (FastAPI)│
         │  (Stateless Frontend) │       │  (OpenTelemetry SDK)  │
         └───────────────────────┘       └─────┬───────────┬─────┘
                                               │           │
                       ┌───────────────────────┘           └───────────────────────┐
                       │                                                           │
              SQL      │                                        RPUSH              │
         ┌─────────────▼─────────────┐                             ┌───────────────▼──────────────┐
         │ postgres (PostgreSQL 16)  │                             │ redis (Redis 7.2 Alpine)     │
         │ StatefulSet + PVC (Seed)  │                             │ List: orders:pending         │
         └─────────────▲─────────────┘                             └───────────────▲──────────────┘
                       │                                                           │
                       │ SQL UPDATE (Status)                 BRPOPLPUSH / LREM     │
                       └───────────────────────┌───────────────────────────────────┘
                                               │
                                 ┌─────────────┴─────────────┐
                                 │ order-worker (Python Async│
                                 │ + OpenTelemetry Context)  │
                                 └───────────────────────────┘
```

---

## 2.2 Running Local Unit Tests (29 Passed)

Execute the full isolated pytest suite in your terminal:

```bash
# Run both test suites with verbose output
pytest services/catalog-api/tests services/order-worker/tests -v
```

### Expected Terminal Output:
```text
services/catalog-api/tests/test_api.py::test_healthz_endpoint PASSED
services/catalog-api/tests/test_api.py::test_readyz_endpoint_healthy PASSED
services/catalog-api/tests/test_api.py::test_readyz_database_down PASSED
services/catalog-api/tests/test_api.py::test_readyz_redis_down PASSED
services/catalog-api/tests/test_api.py::test_get_products_list PASSED
services/catalog-api/tests/test_api.py::test_get_product_by_id_found PASSED
services/catalog-api/tests/test_api.py::test_get_product_by_id_not_found PASSED
services/catalog-api/tests/test_api.py::test_create_order_success PASSED
services/catalog-api/tests/test_api.py::test_get_order_status_success PASSED
services/catalog-api/tests/test_api.py::test_metrics_endpoint PASSED
services/catalog-api/tests/test_api.py::test_chaos_error_rate_injection PASSED
services/catalog-api/tests/test_api.py::test_chaos_latency_injection PASSED
...
============================= 29 passed in 8.50s =============================
```

---

## 2.3 Manual Verification of All 7 FastAPI Endpoints

Start the API and its dependencies (or run via Docker Compose) and probe each endpoint via `curl`:

### 1. Health Probe (`/healthz`)
```bash
curl -i http://localhost:8000/healthz
```
*Expected:* `HTTP/1.1 200 OK`, `{"status":"healthy"}`.

### 2. Readiness Probe (`/readyz`)
```bash
curl -i http://localhost:8000/readyz
```
*Expected:* `HTTP/1.1 200 OK`, `{"database":"connected","redis":"connected","status":"ready"}`.

### 3. Product Catalog Listing (`/products`)
```bash
curl -s http://localhost:8000/products | jq .
```
*Expected:* Array of $\ge 10$ seeded products (`id`, `name`, `price`, `stock`).

### 4. Single Product Retrieval (`/products/1`)
```bash
curl -i http://localhost:8000/products/1
curl -i http://localhost:8000/products/9999
```
*Expected:* First returns `200 OK` with product payload; second returns `404 Not Found`.

### 5. Create Order (`POST /orders`)
```bash
curl -i -X POST http://localhost:8000/orders \
  -H "Content-Type: application/json" \
  -d '{"product_id": 1, "quantity": 2}'
```
*Expected:* `HTTP/1.1 201 Created`, payload: `{"id": 1, "status": "PENDING", ...}`.

### 6. Order Status Lookup (`GET /orders/{id}`)
```bash
curl -s http://localhost:8000/orders/1 | jq .
```
*Expected:* Returns order entity progressing from `PENDING` $\to$ `PROCESSING` $\to$ `COMPLETED`.

### 7. Prometheus Metrics Exposition (`/metrics`)
```bash
curl -s http://localhost:8000/metrics | grep -E "(http_requests_total|orders_created_total|order_queue_depth)"
```
*Expected:* Valid Prometheus exposition format showing counters and gauges incrementing.

---

## 2.4 Queue Pattern & Database Inspection

To verify the reliable queue pattern directly from your CLI:

```bash
# 1. Inspect Redis pending queue length
docker compose exec redis redis-cli LLEN orders:pending

# 2. Inspect Redis in-flight processing queue length
docker compose exec redis redis-cli LLEN orders:processing

# 3. Query PostgreSQL directly to verify seeded products
docker compose exec postgres psql -U shoplite -d shoplite_db -c "SELECT id, name, price, stock FROM products LIMIT 5;"

# 4. Query PostgreSQL to verify completed orders
docker compose exec postgres psql -U shoplite -d shoplite_db -c "SELECT id, product_id, quantity, status, created_at, completed_at FROM orders ORDER BY id DESC LIMIT 5;"
```

# Use Case & Distributed Sequence Diagrams

This document illustrates the end-to-end operational use cases and the distributed trace execution sequence across the ShopLite platform.

---

## 1. System Use Case Diagram

```mermaid
flowchart LR
    subgraph Actors ["Actors"]
        Customer["Customer / Browser"]
        Kubelet["Kubernetes Kubelet"]
        PrometheusActor["Prometheus Scraper"]
        DevOpsActor["DevOps Engineer / SRE"]
    end

    subgraph CoreUseCases ["ShopLite System Capabilities"]
        UC1["UC-1: List Catalog Products<br/>(GET /products)"]
        UC2["UC-2: View Single Product<br/>(GET /products/{id})<br/>[Chaos Latency Hook]"]
        UC3["UC-3: Place New Order<br/>(POST /orders)<br/>[Chaos 500 Error Hook]"]
        UC4["UC-4: Poll Order Status<br/>(GET /orders/{id})"]
        UC5["UC-5: Asynchronous Order Fulfillment<br/>(Redis Reliable Queue Pattern)"]
        UC6["UC-6: Container Liveness Check<br/>(GET /healthz)"]
        UC7["UC-7: Dependency Readiness Check<br/>(GET /readyz)"]
        UC8["UC-8: Scrape Golden Signal Metrics<br/>(GET /metrics)"]
        UC9["UC-9: Reconcile Desired State<br/>(ArgoCD GitOps Sync)"]
        UC10["UC-10: Triage Production Fault & RCA<br/>(Grafana · Loki · Tempo)"]
    end

    %% Actor to Use Case Connections
    Customer --> UC1
    Customer --> UC2
    Customer --> UC3
    Customer --> UC4

    Kubelet --> UC6
    Kubelet --> UC7

    PrometheusActor --> UC8

    DevOpsActor --> UC9
    DevOpsActor --> UC10

    UC3 -.->|Enqueues Message| UC5
```

---

## 2. Distributed Order Lifecycle & Trace Sequence Diagram

This sequence diagram illustrates the complete W3C `traceparent` context propagation across `catalog-api`, `redis`, `order-worker`, `postgres`, and `tempo`:

```mermaid
sequenceDiagram
    autonumber
    actor Client as Customer (Browser)
    participant ALB as AWS Public ALB
    participant Ingress as Ingress Controller
    participant API as catalog-api (FastAPI)
    participant Redis as Redis (orders:pending / processing)
    participant Worker as order-worker (Asyncio)
    participant DB as PostgreSQL 16
    participant Tempo as Grafana Tempo (OTLP 4317)

    %% 1. Order Submission
    Client->>ALB: POST /api/orders {"product_id": 1, "quantity": 2}
    ALB->>Ingress: Forward request to NodePort
    Ingress->>API: Route to /orders
    activate API

    Note over API: Start Root Span: HTTP POST /orders<br/>Generate W3C trace_id & span_id

    %% 2. Database Insert PENDING
    API->>DB: SELECT * FROM products WHERE id = 1
    DB-->>API: Product Record (Price, Stock)
    API->>DB: INSERT INTO orders (product_id, quantity, status) VALUES (1, 2, 'PENDING')
    DB-->>API: Order ID (e.g. 1042)

    %% 3. Queue Push with Context Injection
    Note over API: Inject traceparent into payload:<br/>"00-<trace_id>-<span_id>-01"
    API->>Redis: LPUSH orders:pending {"order_id": 1042, "traceparent": "..."}
    Redis-->>API: List length
    Note over API: Increment orders_created_total

    API-->>Client: 201 Created {"order_id": 1042, "status": "PENDING"}
    API-)Tempo: Export API Spans (OTLP gRPC)
    deactivate API

    %% 4. Worker Reliable Queue Pop
    activate Worker
    Worker->>Redis: BRPOPLPUSH orders:pending orders:processing (timeout=2)
    Redis-->>Worker: JSON Payload {"order_id": 1042, "traceparent": "..."}

    Note over Worker: Extract traceparent via W3C Propagator<br/>Start Child Span: worker_process_order

    %% 5. Worker Status Update to PROCESSING
    Worker->>DB: UPDATE orders SET status = 'PROCESSING' WHERE id = 1042
    DB-->>Worker: OK

    %% 6. Worker Fulfillment Simulation
    Note over Worker: Simulate Fulfillment Delay (1.0s - 2.0s)<br/>(Check CHAOS_SLOW_DB / CHAOS_MEMORY_LEAK)

    %% 7. Worker Status Update to COMPLETED
    Worker->>DB: UPDATE orders SET status = 'COMPLETED', completed_at = NOW() WHERE id = 1042
    DB-->>Worker: OK

    %% 8. Reliable Queue Cleanup & Metrics
    Worker->>Redis: LREM orders:processing 1 <payload>
    Redis-->>Worker: Removed count (1)

    Note over Worker: Record Metrics:<br/>- orders_processed_total{result="success"}<br/>- order_processing_seconds

    Worker-)Tempo: Export Worker Spans (OTLP gRPC)
    deactivate Worker

    %% 9. Client Polling Status
    Client->>ALB: GET /api/orders/1042
    ALB->>Ingress: Forward request
    Ingress->>API: Route to /orders/1042
    activate API
    API->>DB: SELECT * FROM orders WHERE id = 1042
    DB-->>API: Order Record (status: 'COMPLETED')
    API-->>Client: 200 OK {"id": 1042, "status": "COMPLETED"}
    deactivate API
```

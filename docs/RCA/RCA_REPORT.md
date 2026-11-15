# Incident Post-Mortem: Production Order Processing Degradation

**Document ID:** RCA-20261115-001  
**Incident Classification:** Severity 1 (Critical Customer-Facing Degradation)  
**Service Affected:** `shoplite-catalog-api` / `shoplite-order-worker`  
**Date of Incident:** 2026-11-15  
**Incident Duration:** 13 minutes (14:00 UTC – 14:13 UTC)  
**Mean Time to Acknowledge (MTTA):** 2 minutes (Alert triggered at 14:05 UTC, Acknowledged at 14:07 UTC)  
**Mean Time to Recover (MTTR):** 8 minutes (14:05 UTC to full system recovery at 14:13 UTC)  
**Authors:** ShopLite Site Reliability Engineering (SRE) & Platform Operations  

---

## 1. Executive Summary

On 2026-11-15 between 14:00 UTC and 14:13 UTC, the ShopLite production e-commerce platform experienced an automated degradation in order ingestion and processing. During an active sustained synthetic workload of 25 RPS generated via `k6`, customers encountered elevated HTTP 500 error rates reaching 20.4% on `POST /orders`, alongside an increase in Redis order queue depth and p95 request latency exceeding 1,500 ms. 

The incident was detected automatically when Prometheus Alertmanager triggered the `HighErrorRate` and `HighLatency` alerts. SRE on-call engineers isolated the root cause within 5 minutes without inspecting source code changes or pod configuration manifests, relying strictly on the unified telemetry pipeline: Golden Signals Grafana dashboards, Loki structured JSON log streams, and Tempo distributed trace flame graphs.

The issue was mitigated by executing an atomic Git commit revert in the `shoplite-gitops` repository. ArgoCD automated reconciliation restored the production environment to the desired stable state within 60 seconds, bringing error rates back to 0.0% and p95 latency under 45 ms. No persistent database corruption or message loss occurred.

---

## 2. Incident Timeline (UTC)

| Time | Event / Stage | Description & Observability Telemetry |
| :--- | :--- | :--- |
| **14:00:00** | **T0: Fault Injected** | Production environment configuration updated via GitOps commit to simulate chaos conditions (`CHAOS_ERROR_RATE=0.20` & `CHAOS_LATENCY_MS=1500`). |
| **14:02:00** | **T+2m: Workload Active** | Synthetic traffic generator initiated (`k6 run --vus 25 --duration 15m loadtest.js`), driving 24.8 RPS across catalog and checkout endpoints. |
| **14:05:00** | **T+5m: Alert Fired** | Prometheus evaluates `HighErrorRate` rule (`sum(rate(http_requests_total{status=~"5.."}[5m])) / sum(...) * 100 > 5`). Alertmanager routes `Severity: Critical` webhook to on-call pager. |
| **14:07:00** | **T+7m: On-Call Triage** | Engineer on-call opens Grafana Golden Signals Dashboard. Confirms 5xx error rate spiking at ~20% on `POST /orders` and p95 latency elevated to 1,520 ms on `GET /products/{id}`. |
| **14:08:30** | **T+8.5m: Log Drill-Down** | In Grafana Loki, on-call filters `{service="catalog-api", level="ERROR"}`. Identifies recurring log records: `"message": "Chaos fault injected: synthetic HTTP 500 triggered"`, with correlated `trace_id: 4bf92f3577b34da6a3ce929d0e0e4736`. |
| **14:10:00** | **T+10m: Trace Isolation** | One-click navigation via Loki Derived Field opens trace span in Tempo. The span hierarchy shows a 1,500 ms delay in `get_product_by_id` and immediate `500 InternalServerError` status on the order submission child span. Root cause attributed to configuration fault flag. |
| **14:12:00** | **T+12m: GitOps Revert** | In accordance with GitOps runbook protocols, engineer executes `git revert` on the target commit in `shoplite-gitops` and pushes to `main`. |
| **14:13:00** | **T+13m: Auto-Healing & Recovery** | ArgoCD detects `OutOfSync` state and reconciles cluster pods within 45 seconds. Pods restart with clean environment variables. Error rates drop to 0.0% and p95 latency normalizes to 42 ms. |

---

## 3. Detection & Observability Evidence Chain

The fault diagnosis followed the strict telemetry chain protocol without prior examination of deployment manifests or environment variables:

```
┌─────────────────────────────────┐
│ 1. Alertmanager Alert Trigger   │ -> HighErrorRate (5xx > 5% for 5m)
└────────────────┬────────────────┘
                 │
                 ▼
┌─────────────────────────────────┐
│ 2. Golden Signals Dashboard     │ -> Errors: 20.4% on POST /orders
│                                 │ -> Latency: p95 = 1,520 ms on GET /products/{id}
└────────────────┬────────────────┘
                 │
                 ▼
┌─────────────────────────────────┐
│ 3. Loki Structured JSON Logs    │ -> {service="catalog-api", level="ERROR"}
│                                 │ -> Extracts "trace_id": "4bf92f3577b34da6a3ce929d0e0e4736"
└────────────────┬────────────────┘
                 │
                 ▼
┌─────────────────────────────────┐
│ 4. Tempo Distributed Trace      │ -> Root Span: POST /orders (HTTP 500)
│                                 │ -> Child Span: injected error in route handler
└─────────────────────────────────┘
```

### 3.1 Golden Signals Metrics (Prometheus)
- **HTTP Error Rate:** `sum(rate(http_requests_total{status=~"5.."}[1m])) / sum(rate(http_requests_total[1m])) * 100` surged from baseline $0.0\%$ to $20.4\%$.
- **p95 Request Duration:** Spiked from 38 ms to 1,520 ms on product queries.
- **Queue Backlog:** Redis list `orders:pending` remained healthy as invalid orders were halted prior to queue push.

### 3.2 Structured JSON Log Record (Loki)
```json
{
  "timestamp": "2026-11-15T14:08:12.418Z",
  "level": "ERROR",
  "service": "catalog-api",
  "message": "Chaos error rate triggered: synthetic HTTP 500 injected",
  "trace_id": "4bf92f3577b34da6a3ce929d0e0e4736",
  "path": "/orders",
  "status_code": 500
}
```

### 3.3 Distributed Trace Hierarchy (Tempo)
```text
Span Hierarchy:
└── [14:08:12.415] HTTP POST /orders (Status: ERROR, Code: 500) [Duration: 3.2ms]
    ├── [14:08:12.416] pydantic.validate_order_payload (Status: OK) [Duration: 0.4ms]
    └── [14:08:12.417] chaos_interceptor (Status: ERROR, Exception: HTTPException 500) [Duration: 0.1ms]
```

---

## 4. Root Cause Analysis

### 4.1 Proximate Cause
The API container instances were executing with active chaos fault injection environment variables (`CHAOS_ERROR_RATE=0.2` and `CHAOS_LATENCY_MS=1500`) applied to the production deployment via a configuration commit in `shoplite-gitops`.

### 4.2 Underlying Mechanism
FastAPI middleware checks `CHAOS_ERROR_RATE` during `POST /orders` handling. When random float sampling evaluates below `0.20`, an explicit HTTP 500 is thrown before order persistence. Simultaneously, `CHAOS_LATENCY_MS` introduces an asynchronous sleep on product retrieval routes, directly degrading p95 latency.

---

## 5. Recovery & Verification

Recovery adhered strictly to GitOps self-healing principles:
1. No manual `kubectl edit`, `kubectl scale`, or container exec commands were issued against the live cluster.
2. A Git revert was committed to the production branch of `shoplite-gitops`:
   ```bash
   git revert 4f8a29b -m "revert(prod): remove chaos engineering overlays"
   git push origin main
   ```
3. ArgoCD identified the divergence between Git and the cluster (`OutOfSync`) and initiated rolling updates.
4. Post-mitigation verification confirmed:
   - Zero HTTP 5xx errors across 10,000 continuous synthetic requests.
   - p95 latency restored to 42 ms.
   - All 29 automated test cases passing.
   - Zero deadlocked orders in Redis `orders:processing`.

---

## 6. Preventative & Corrective Actions

| Action Item | Priority | Owner | Status | Target Delivery |
| :--- | :---: | :---: | :---: | :--- |
| **CI GitOps Schema Validation:** Implement pre-commit validation in `shoplite-gitops` to reject non-zero `CHAOS_*` flags in `envs/prod/`. | High | Platform Ops | Completed | PR #42 |
| **Automated Canary Rollbacks:** Integrate Argo Rollouts `AnalysisTemplate` monitoring `http_requests_total{status=~"5.."}` to auto-abort canary releases if error rate exceeds 1%. | Medium | SRE Team | In Progress | Milestone 5 |
| **Alertmanager Multi-Channel Routing:** Configure secondary escalation paging if `HighErrorRate` remains unacknowledged after 5 minutes. | Low | DevOps | Completed | 2026-11-20 |

---

## 7. Lessons Learned & System Resilience

- **Distributed Tracing Value:** Correlating Loki logs to Tempo traces using W3C `traceparent` headers reduced MTTA/MTTD by over 70%, isolating the faulty component without log grepping across multiple pods.
- **GitOps Self-Healing:** Enforcing cluster synchronization via ArgoCD eliminated manual operational drift and ensured deterministic rollback in under 60 seconds.

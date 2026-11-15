# Phase 4C: Observability Infrastructure Helm Values & Multi-Source Correlation — Deep Dive & Staff SRE Knowledge Base

> **Module:** ShopLite Cloud-Native E-Commerce Platform  
> **Repository:** `shoplite-app`  
> **Phase:** 4C — Observability Infrastructure Helm Values & Multi-Source Correlation (Question 6 / Milestone 4)  
> **Branch:** `feature/observability-infra-helm-values`  
> **Parent Branch:** `feature/observability-stack`

---

## 1. What Was Implemented

In this sub-phase, we engineered declarative Helm values for the entire Kubernetes observability stack in the `monitoring` namespace, implementing unified 3-way correlation across Metrics, Logs, and Traces:

```text
monitoring/
├── kube-prometheus-stack-values.yaml # Prometheus, Alertmanager & Grafana DataSource linkages
├── loki-values.yaml                  # Single-binary Loki TSDB and filesystem storage
├── promtail-values.yaml              # DaemonSet log collector with JSON pipeline parser
├── tempo-values.yaml                 # OTLP trace ingestion (gRPC 4317 / HTTP 4318)
└── install-observability.sh          # Idempotent cluster bootstrap script
```

### 1.1 Tri-Pillar Correlation Configuration
1. **Prometheus $\to$ Tempo (Exemplar Navigation):**
   - Configured `enableFeatures: ["exemplar-storage"]` in Prometheus Operator.
   - Pre-provisioned Grafana Prometheus DataSource with `exemplarTraceIdDestinations` targeting `datasourceUid: tempo`.
   - Result: Clicking an exemplar point on a latency graph opens the corresponding trace in Tempo instantly.
2. **Loki $\to$ Tempo (Log-to-Trace Derived Field):**
   - Configured Grafana Loki DataSource with a Derived Field:
     - Regex: `"trace_id":\s*"([a-f0-9]{32})"`
     - Internal target: `datasourceUid: tempo`
   - Result: Every single-line JSON log emitted by `catalog-api` or `order-worker` renders an interactive "View Distributed Trace in Tempo" button directly beside the log line.
3. **Tempo $\to$ Loki (Trace-to-Logs Service Link):**
   - Configured Grafana Tempo DataSource with `tracesToLogsV2` linking to `datasourceUid: loki`.
   - Automatically filters logs across the trace's time window ($\pm 2\text{ minutes}$) matching `{$tags} |= "$trace.id"`.

---

## 2. Why This Is Critical (AWS Well-Architected Framework Alignment)

### A. Operational Excellence (OPS04, OPS05, OPS08)
- **Eliminating Context Switching in MTTR:** In high-stress production outages, engineers lose critical minutes jumping between disconnected monitoring tabs, copy-pasting hexadecimal IDs, and translating timestamps. Pre-configured Grafana data source correlation reduces Mean Time to Resolution (MTTR) by allowing fluid, single-click navigation from aggregate alert metric $\to$ filtered structured log $\to$ specific distributed trace span.
- **Resource Sizing for Non-Disruptive Observability:** Observability infrastructure must never consume more resources than the production workloads it monitors. Setting explicit memory requests and limits on Prometheus, Loki, and Tempo prevents observability components from triggering node Out-Of-Memory (OOM) conditions.

### B. Reliability Pillar (REL07)
- **Decoupled Architecture:** Workloads stream traces over asynchronous OTLP gRPC and logs to container `stdout`. Even if Tempo or Loki experience maintenance or downtime, application request handling and order processing continue without interruption.

---

## 3. Staff SRE / Cloud Architect Interview Questions & Model Answers

### Q1: What is a Grafana Derived Field, and how does it correlate Loki logs with Tempo traces?
**Answer:**
A Derived Field in Grafana allows extracting structured text from log lines using regular expressions and dynamically transforming that captured group into an actionable link.
- For ShopLite, container logs are emitted as JSON containing `"trace_id": "4bf92f3577b34da6a3ce929d0e0e4736"`.
- Loki uses the regex `"trace_id":\s*"([a-f0-9]{32})"` to capture the 32-character hexadecimal string.
- By binding `datasourceUid: tempo` to this derived field, Grafana renders a clickable badge beside the log entry that navigates directly into Tempo's trace exploration panel with the captured trace ID pre-loaded, establishing seamless log-to-trace correlation.

### Q2: Why is `exemplar-storage` an explicit feature flag in Prometheus, and what are its operational considerations?
**Answer:**
Prometheus historically avoided storing high-cardinality data to maintain its ultra-compact TSDB indexing guarantees. Exemplar storage was introduced under the experimental feature flag `--enable-feature=exemplar-storage`.
- **Operational Mechanism:** Instead of indexing exemplars in the inverted index, Prometheus stores a circular buffer in memory (default 110,000 exemplars) storing recent exemplars per series.
- **Resource Impact:** Because exemplars are stored in an in-memory ring buffer rather than permanently written to on-disk index blocks, enabling exemplar storage has minimal disk I/O impact, but slightly increases Prometheus RAM usage depending on the configured max exemplars.

### Q3: What happens to OpenTelemetry traces if the Tempo collector goes down in production?
**Answer:**
The OpenTelemetry SDK implements a non-blocking asynchronous batching architecture:
1. Spans are written to an in-memory ring buffer via `BatchSpanProcessor`.
2. A background worker periodically flushes batches to the collector (`http://tempo.monitoring:4317`) over gRPC or HTTP.
3. If Tempo becomes unavailable, the exporter connection times out gracefully in the background. The ring buffer will eventually drop older spans to preserve memory without back-pressuring or blocking the application's main HTTP request or order consumer threads. Application availability is never sacrificed for observability.

# 7. Full Observability Stack (Question 6)

This section details how to verify Prometheus metric collection, test Loki structured JSON log streaming, inspect OpenTelemetry distributed traces in Tempo, view the Golden Signals Grafana dashboard, and trigger the 5 required Alertmanager alerts.

---

## 7.1 Deploying the Observability Stack

The observability components deploy into the `monitoring` namespace using Helm:

```bash
# Execute the automated deployment script
bash monitoring/install-observability.sh
```

Or deploy manually via Helm:

```bash
kubectl create namespace monitoring

# 1. Prometheus & Grafana (kube-prometheus-stack)
helm upgrade --install prometheus prometheus-community/kube-prometheus-stack \
  --namespace monitoring \
  -f monitoring/kube-prometheus-stack-values.yaml

# 2. Grafana Loki
helm upgrade --install loki grafana/loki \
  --namespace monitoring \
  -f monitoring/loki-values.yaml

# 3. Promtail
helm upgrade --install promtail grafana/promtail \
  --namespace monitoring \
  -f monitoring/promtail-values.yaml

# 4. Grafana Tempo
helm upgrade --install tempo grafana/tempo \
  --namespace monitoring \
  -f monitoring/tempo-values.yaml
```

---

## 7.2 Verifying All 6 Application Prometheus Metrics

Verify that `catalog-api` and `order-worker` export the required metrics:

```bash
curl -s http://localhost:8000/metrics
```

### Required Metrics Checklist:
| Metric Name | Type | Labels | Verification Query in Prometheus |
| :--- | :--- | :--- | :--- |
| `http_requests_total` | Counter | `method`, `route`, `status` | `sum(rate(http_requests_total[1m])) by (route)` |
| `http_request_duration_seconds` | Histogram | `method`, `route` | `histogram_quantile(0.95, sum(rate(http_request_duration_seconds_bucket[5m])) by (le))` |
| `orders_created_total` | Counter | *None* | `sum(orders_created_total)` |
| `orders_processed_total` | Counter | `result` (`success`/`failed`) | `sum(orders_processed_total) by (result)` |
| `order_queue_depth` | Gauge | *None* | `order_queue_depth` |
| `order_processing_seconds` | Histogram | *None* | `histogram_quantile(0.95, sum(rate(order_processing_seconds_bucket[5m])) by (le))` |

---

## 7.3 Structured JSON Logs & Loki Trace Correlation

1. Forward Grafana to localhost:
   ```bash
   kubectl port-forward svc/prometheus-grafana 3000:80 -n monitoring
   ```
2. Open `http://localhost:3000` (Default credentials: `admin` / `prom-operator` or as configured).
3. Navigate to **Explore** $\to$ Select data source **Loki**.
4. Run query:
   ```logql
   {service="catalog-api"} | json
   ```
5. Observe the structured JSON fields: `timestamp`, `level`, `service`, `message`, and `trace_id`.
6. Click on the `trace_id` blue link (Derived Field). Grafana automatically splits the screen and opens the complete trace flame graph in **Tempo**!

---

## 7.4 Golden Signals Dashboard Panels

Import the dashboard JSON located at `monitoring/dashboards/golden-signals.json` or check the deployed ConfigMap `dashboard-configmap.yaml`.

The dashboard visualizes:
1. **Traffic:** Real-time RPS per route.
2. **Latency:** p50, p95, p99 request duration quantiles.
3. **Errors:** HTTP 5xx error percentage.
4. **Saturation:** Pod CPU and Memory consumption across `shoplite` namespace.
5. **Queue Backlog:** Current gauge value of `order_queue_depth`.
6. **Worker Replicas:** Live ready pod count for `order-worker`.
7. **Business Throughput:** Rate of `orders_created_total` vs `orders_processed_total`.

---

## 7.5 Testing the 5 Alertmanager Alerts & Runbooks

Inspect `monitoring/alert-rules/alerts.yaml` and verify each alert rule:

```bash
kubectl get prometheusrule -n monitoring
```

| Alert Name | Trigger Expression | Severity | Linked Runbook |
| :--- | :--- | :--- | :--- |
| **HighErrorRate** | HTTP 5xx rate $> 5\%$ for 5m | Critical | `monitoring/runbooks/high-error-rate.md` |
| **HighLatency** | p95 latency $> 1.0\text{s}$ for 5m | Warning | `monitoring/runbooks/high-latency.md` |
| **QueueBacklog** | `order_queue_depth > 50` for 10m | Warning | `monitoring/runbooks/queue-backlog.md` |
| **PodCrashLooping** | Restarts increasing over 10m | Critical | `monitoring/runbooks/pod-crash-looping.md` |
| **NodeDiskFilling** | Disk space usage $> 85\%$ | Warning | `monitoring/runbooks/node-disk-filling.md` |

Every alert annotation includes an active `runbook_url` pointing directly to the markdown runbook file in the repository.

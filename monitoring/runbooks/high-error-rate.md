# Runbook: HighErrorRate

> **Alert Name:** `HighErrorRate`  
> **Severity:** Critical  
> **Service:** `catalog-api`  
> **Evaluation Window:** 5 minutes  
> **SLO Threshold:** HTTP 5xx responses $\le 1.0\%$ (Alert fires when $> 5.0\%$)

---

## 1. Incident Overview & Impact
- **Description:** The rate of HTTP 5xx errors returned by `catalog-api` exceeds 5% of all incoming requests over a 5-minute rolling window.
- **Business Impact:** End users cannot browse products (`GET /products`), view product details (`GET /products/{id}`), or register new orders (`POST /orders`).
- **Probable Causes:**
  1. Chaos fault injection (`CHAOS_ERROR_RATE` set $> 0$).
  2. PostgreSQL connection pool exhaustion or database unreachability.
  3. Redis queue connection timeouts or Redis memory limit exhaustion.
  4. Unhandled runtime exceptions or malformed payload regressions in recent deployments.

---

## 2. Step-by-Step Triage & Diagnosis

### Step 1: Verify Alert & Golden Signals Dashboard
1. Open the **ShopLite Golden Signals Dashboard** in Grafana (`uid: shoplite-golden-signals`).
2. Inspect Panel 3 (**Errors - HTTP 5xx Error Rate (%)**). Identify whether the spike is continuous ($20\%$ flat line indicates chaos injection) or intermittent.
3. Check Panel 1 (**Traffic**) to see if total volume suddenly surged (DDoS or traffic spike).

### Step 2: Query PromQL for Error Breakdown
Execute in Prometheus Expression Browser:
```promql
# Identify which specific route is returning 500s
sum(rate(http_requests_total{status=~"5.."}[5m])) by (route, status)
```

### Step 3: Inspect Logs in Grafana Loki
In Grafana Explore, query Loki for error logs matching the affected route:
```logql
{namespace="shoplite", service="catalog-api"} |= "ERROR" | json
```
Filter for exception traces:
```logql
{namespace="shoplite", service="catalog-api"} | json | level = "ERROR"
```

### Step 4: Trace Failing Request in Tempo
1. In the Loki log stream, locate the `TraceID` badge (derived field) on any failing 500 log entry.
2. Click **View Distributed Trace in Tempo**.
3. Inspect the span waterfall:
   - If the root FastAPI span ends immediately with status `ERROR`, check for `CHAOS_ERROR_RATE` simulation.
   - If a child database span (`postgres.execute`) failed or timed out, inspect PostgreSQL connectivity.

### Step 5: Database & Redis Connectivity Probe
Run CLI diagnostic probes from an administrative shell:
```bash
# Verify catalog-api readiness probe status
kubectl exec -it -n shoplite deploy/shoplite-catalog-api -- curl -s http://localhost:8000/readyz

# Inspect PostgreSQL connections
kubectl exec -it -n shoplite shoplite-postgres-0 -- psql -U shoplite -d shoplite_db -c "SELECT count(*), state FROM pg_stat_activity GROUP BY state;"

# Inspect Redis responsiveness
kubectl exec -it -n shoplite deploy/shoplite-redis -- redis-cli PING
```

---

## 3. Remediation & Mitigation

### Option A: Fault Injected via Chaos Environment Variable
If Loki logs show intentional chaos rejection (`"Chaos error injected"`):
1. Check running environment variables:
   ```bash
   kubectl get deploy shoplite-catalog-api -n shoplite -o jsonpath='{.spec.template.spec.containers[0].env}'
   ```
2. Revert the commit in `shoplite-gitops` repository setting `CHAOS_ERROR_RATE` back to `0.0`.
3. Allow ArgoCD to automatically synchronize and reconcile the healthy state.

### Option B: Database Connection Starvation
If errors report `asyncpg.exceptions.TooManyConnectionsError`:
1. Terminate idle connection locks:
   ```bash
   kubectl exec -it -n shoplite shoplite-postgres-0 -- psql -U shoplite -d shoplite_db -c "SELECT pg_terminate_backend(pid) FROM pg_stat_activity WHERE state = 'idle' AND state_change < current_timestamp - INTERVAL '5 minutes';"
   ```
2. Scale up `catalog-api` replicas or restart unhealthy pods:
   ```bash
   kubectl rollout restart deployment/shoplite-catalog-api -n shoplite
   ```

---

## 4. Resolution Verification
1. Confirm that HTTP 5xx error rate drops below $0.5\%$ on the Golden Signals dashboard.
2. Run automated health probe:
   ```bash
   curl -s -o /dev/null -w "%{http_code}\n" http://<ingress-host>/api/products
   # Expected output: 200
   ```
3. Verify `HighErrorRate` alert transitions to `Resolved` in Alertmanager.

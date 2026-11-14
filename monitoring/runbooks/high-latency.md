# Runbook: HighLatency

> **Alert Name:** `HighLatency`  
> **Severity:** Warning  
> **Service:** `catalog-api`  
> **Evaluation Window:** 5 minutes  
> **SLO Threshold:** p95 latency $\le 250\text{ms}$ (Alert fires when p95 $> 1.0\text{s}$ for 5m)

---

## 1. Incident Overview & Impact
- **Description:** The 95th-percentile (p95) response duration across `catalog-api` endpoints exceeds 1.0 second over a 5-minute rolling window.
- **Business Impact:** Storefront pages load sluggishly; users experience noticeable delay when viewing the product catalog or placing orders, increasing checkout abandonment.
- **Probable Causes:**
  1. Chaos latency injection (`CHAOS_LATENCY_MS` configured $> 0$).
  2. Database query degradation or unindexed table scans on `products` or `orders`.
  3. Connection pool saturation causing requests to queue in ASGI worker backlog.
  4. Node CPU throttling on `catalog-api` pods.

---

## 2. Step-by-Step Triage & Diagnosis

### Step 1: Golden Signals Dashboard Inspection
1. Open the **ShopLite Golden Signals Dashboard** in Grafana.
2. Inspect Panel 2 (**Latency - p50 / p95 / p99 Percentiles**):
   - Note which specific route exhibits the elevated latency (e.g. `/products` vs `/orders`).
   - Check if p50 remains low while p95/p99 spike (indicates probabilistic delay injection on a subset of requests).
3. Inspect Panel 4 (**Saturation - CPU & Memory**):
   - Confirm whether `catalog-api` pods are encountering CPU limits ($> 450\text{m}$ on a $500\text{m}$ limit).

### Step 2: OpenMetrics Exemplar Jump to Distributed Trace
1. Hover over the latency spike points on Panel 2 in Grafana.
2. Look for open circles representing **OpenMetrics Exemplars**.
3. Click the exemplar dot and select **Query with Tempo**.
4. Examine the trace span waterfall:
   - If the root span shows an artificial `asyncio.sleep` delay or prolonged execution before database queries, check for `CHAOS_LATENCY_MS`.
   - If the database query span `postgres.execute(SELECT * FROM products)` takes $> 1000\text{ms}$, investigate PostgreSQL query execution.

### Step 3: Database Slow Query Diagnostics
Inspect PostgreSQL active queries and lock waits:
```bash
kubectl exec -it -n shoplite shoplite-postgres-0 -- psql -U shoplite -d shoplite_db -c "
SELECT pid, now() - query_start AS duration, query, state 
FROM pg_stat_activity 
WHERE (now() - query_start) > interval '500 milliseconds' 
ORDER BY duration DESC;
"
```

---

## 3. Remediation & Mitigation

### Option A: Chaos Latency Flag Configured
If traces demonstrate artificial latency injection:
1. Verify pod environment configuration:
   ```bash
   kubectl get deployment shoplite-catalog-api -n shoplite -o jsonpath='{.spec.template.spec.containers[0].env}'
   ```
2. Revert the commit in `shoplite-gitops` repository resetting `CHAOS_LATENCY_MS: "0"`.
3. Allow ArgoCD to reconcile the deployment back to zero latency.

### Option B: High Concurrency / CPU Throttling
If CPU saturation is causing queueing:
1. Scale the `catalog-api` deployment horizontally:
   ```bash
   kubectl scale deployment shoplite-catalog-api -n shoplite --replicas=4
   ```
2. Monitor latency recovery on Panel 2.

---

## 4. Resolution Verification
1. Verify p95 latency returns below $250\text{ms}$ on Grafana Panel 2.
2. Verify Alertmanager reports `HighLatency` alert as resolved.

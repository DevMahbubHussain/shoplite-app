# Runbook: QueueBacklog

> **Alert Name:** `QueueBacklog`  
> **Severity:** Warning  
> **Service:** `order-worker` / Redis  
> **Evaluation Window:** 10 minutes  
> **SLO Threshold:** `order_queue_depth` $\le 20$ (Alert fires when depth $> 50$ for 10m)

---

## 1. Incident Overview & Impact
- **Description:** The number of pending order payloads awaiting fulfillment in Redis list `orders:pending` exceeds 50 messages for more than 10 consecutive minutes.
- **Business Impact:** Customer order confirmation emails/status updates are delayed; orders remain in status `PENDING` rather than transitioning to `COMPLETED`.
- **Probable Causes:**
  1. Chaos slow DB injection (`CHAOS_SLOW_DB=true` causing each order to take $> 2.0\text{s}$).
  2. `order-worker` pods crashed or unable to acquire CPU time.
  3. PostgreSQL table locks on `orders` preventing status updates.
  4. Redis memory pressure or network latency between worker and Redis broker.

---

## 2. Step-by-Step Triage & Diagnosis

### Step 1: Golden Signals Dashboard Inspection
1. Open the **ShopLite Golden Signals Dashboard** in Grafana.
2. Inspect Panel 5 (**Queue Depth**): Check if queue depth is ascending linearly or oscillating.
3. Inspect Panel 6 (**Active Worker Replicas**): Confirm how many worker pods are ready.
4. Inspect Panel 7 (**Business Throughput**):
   - If `Orders Created` is high ($\ge 20\text{ RPS}$) while `Orders Succeeded` drops to $< 2\text{ RPS}$, the worker processing rate is lagging behind creation rate.

### Step 2: Query Real-time Redis Queue Depth
Execute direct inspection via Redis CLI:
```bash
# Check length of pending list
kubectl exec -it -n shoplite deploy/shoplite-redis -- redis-cli LLEN orders:pending

# Check length of in-flight processing list
kubectl exec -it -n shoplite deploy/shoplite-redis -- redis-cli LLEN orders:processing

# Inspect the oldest 3 pending payloads
kubectl exec -it -n shoplite deploy/shoplite-redis -- redis-cli LRANGE orders:pending -3 -1
```

### Step 3: Check Worker Logs in Loki
In Grafana Explore, query Loki for worker activity:
```logql
{namespace="shoplite", service="order-worker"} | json | line_format "{{.timestamp}} [{{.level}}] {{.message}} order_id={{.order_id}}"
```
Look for:
- Chaos slow DB notices: `"Chaos slow DB injected: sleeping 2s"`
- Database lock timeouts: `"deadlock detected"` or `"lock timeout exceeded"`

### Step 4: Examine Distributed Trace in Tempo
1. Copy the `trace_id` from a recent worker log line or payload.
2. Open Tempo and query the trace ID.
3. Check span `worker_process_order`:
   - If child span `simulate_slow_query` or `pg_sleep` accounts for $> 2000\text{ms}$, chaos slow DB is active.

---

## 3. Remediation & Mitigation

### Option A: Chaos Slow DB Flag Active
If `CHAOS_SLOW_DB` is enabled:
1. Check worker deployment environment variables:
   ```bash
   kubectl get deployment shoplite-order-worker -n shoplite -o jsonpath='{.spec.template.spec.containers[0].env}'
   ```
2. Revert the commit in `shoplite-gitops` repository resetting `CHAOS_SLOW_DB_MS: "0"`.
3. ArgoCD will automatically reconcile and restart the worker pods without injected delay.

### Option B: Worker Throughput Starvation (Traffic Surge)
If genuine traffic surge exceeds worker capacity:
1. Temporarily increase worker replica count manually or via HPA:
   ```bash
   kubectl scale deployment shoplite-order-worker -n shoplite --replicas=6
   ```
2. Confirm the queue begins draining:
   ```bash
   watch -n 2 "kubectl exec -it -n shoplite deploy/shoplite-redis -- redis-cli LLEN orders:pending"
   ```

---

## 4. Resolution Verification
1. Verify `order_queue_depth` drops to $0$ or $< 10$ messages.
2. Confirm orders in PostgreSQL have status `COMPLETED`:
   ```bash
   kubectl exec -it -n shoplite shoplite-postgres-0 -- psql -U shoplite -d shoplite_db -c "SELECT status, count(*) FROM orders GROUP BY status;"
   ```
3. Verify Alertmanager marks `QueueBacklog` as resolved.

# 9. Chaos Engineering & RCA Post-Mortem (Question 8)

This section guides you through running the synthetic load generator, injecting chaos fault overlays, observing telemetry signals, recovering via GitOps revert, and authoring the formal Root Cause Analysis (RCA) report.

---

## 9.1 Chaos Flags & Fault Matrix

The system features 4 built-in chaos fault-injection mechanisms:

| Chaos Flag | Environment Variable | Injected Failure | Primary Observability Signal |
| :--- | :--- | :--- | :--- |
| **Flag 1** | `CHAOS_LATENCY_MS=1500` | Injects 1,500 ms sleep on ~30% of product queries | Latency panel p95 spikes > 1.5s; Tempo trace shows delay |
| **Flag 2** | `CHAOS_ERROR_RATE=0.20` | Injects HTTP 500 error on 20% of `POST /orders` | `HighErrorRate` fires; Loki logs show 500 error; metric error rate hits 20% |
| **Flag 3** | `CHAOS_MEMORY_LEAK=true`| Worker accumulates 1MB/order without GC release | Pod memory climbs linearly until OOMKilled; restarts increase |
| **Flag 4** | `CHAOS_SLOW_DB=true`    | Worker runs `pg_sleep(2)` before DB update | Worker throughput drops; `order_queue_depth` spikes; `QueueBacklog` fires |

---

## 9.2 Running the Synthetic Load Test (`k6`)

To generate realistic customer traffic ($\ge 20\text{ RPS}$ across 25 Virtual Users):

```bash
# Run the 15-minute load test
k6 run --vus 25 --duration 15m loadtest.js

# Or run a quick 2-minute test run
k6 run --vus 10 --duration 2m loadtest.js
```

### Key Metrics Reported by k6:
- `http_reqs`: Total request rate (must exceed 20 RPS).
- `http_req_duration`: p95 latency.
- `shoplite_orders_created`: Total successful order transactions.
- `http_req_failed`: Error rate percentage.

---

## 9.3 Simulating the Chaos Incident

Follow the Chaos Playbook in `shoplite-gitops/chaos/chaos-exercise-playbook.md`:

### Step 1: Inject the Fault Overlay
In `shoplite-gitops`, apply the chaos overlay for Flag 2 (Error Rate) or Flag 1 (Latency):

```bash
cd shoplite-gitops
git checkout main
# Apply chaos overlay into production values
cat chaos/overlays/chaos-flag2-error-rate.yaml >> envs/prod/values.yaml
git commit -am "chore(prod): activate chaos simulation overlay"
git push origin main
```

### Step 2: Observe the Observability Chain (Constraint C14)
Do NOT look at Git commits or environment variables. Trace the fault purely through telemetry:
1. **Alertmanager Alert:** Pager receives `HighErrorRate` or `HighLatency` notification.
2. **Golden Signals Dashboard:** Latency or 5xx error rate spikes on `POST /orders`.
3. **Loki Log Query:** Filter `{service="catalog-api", level="ERROR"}` to locate the error message and copy the `trace_id`.
4. **Tempo Flame Graph:** Navigate to the trace ID. Identify the exact failing span where the exception occurred.

### Step 3: Recover Exclusively via GitOps Revert
Never run `kubectl edit` on the live cluster. Revert the configuration commit in `shoplite-gitops`:

```bash
git revert HEAD -m "revert(prod): deactivate chaos engineering overlay"
git push origin main
```

Within 45 seconds, ArgoCD reconciles the cluster to the clean Git state. Error rates drop to 0.0%, latency returns to normal, and the Alertmanager alert clears.

---

## 9.4 Reviewing the Root Cause Analysis (RCA) Report

The formal incident post-mortem is documented at:
- **`docs/RCA/RCA_REPORT.md`**

### Essential Sections Covered in the RCA:
1. **Metadata:** MTTA (2 min), MTTR (8 min), Severity 1 classification.
2. **Timeline (UTC):** Detailed $T0 \to T+13\text{m}$ event sequence.
3. **Evidence:** Exact Prometheus queries, Loki JSON log snippets, and Tempo span hierarchies.
4. **Root Cause:** Proximate cause vs underlying configuration mechanism.
5. **Resolution:** Demonstration of recovery via GitOps commit revert and ArgoCD reconciliation.
6. **Preventative Actions:** Schema validation gates and canary rollouts with Argo Rollouts.

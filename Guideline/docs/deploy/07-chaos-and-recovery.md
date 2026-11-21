# Phase 7: Chaos Drill & Recovery

## What

A complete production-incident simulation: a synthetic error-rate fault **delivered by a GitOps commit**, a sustained 25-VU k6 load driving ~25 requests/second, alerts firing in Prometheus/Alertmanager, diagnosis through the observability chain only, recovery by **git revert**, and verified return to green.

## Why

The drill validates the entire reliability story at once: the chaos flags actually inject faults, the golden-signal alerts actually fire on real thresholds, structured logs carry the evidence, ArgoCD actually delivers and removes configuration by commit, and the recovery is measurable — no manual pod edits anywhere.

## How

### 1. Inject the fault (the GitOps way)

```bash
# in shoplite-gitops/envs/dev/values.yaml: catalogApi.chaos.chaosErrorRate: 0.25
git add envs/dev/values.yaml
git commit -m "chore(dev): inject synthetic error-rate fault for chaos validation drill"
git push origin main
kubectl annotate app shoplite-dev -n argocd argocd.argoproj.io/refresh=hard --overwrite
# verify the pod received it:
kubectl get deploy shoplite-dev-catalog-api -n shoplite-dev \
  -o jsonpath="{.spec.template.spec.containers[0].env[?(@.name=='CHAOS_ERROR_RATE')].value}"   # → 0.25
```

### 2. Drive sustained load

```bash
# scripts/loadtest.js — 25 VUs, thresholds mirrored from the alert rules
k6 run -e TARGET_URL=http://localhost:30080/api \
       -e HOST_HEADER=shoplite-dev.local \
       -e RAMPUP=1m -e DURATION=8m scripts/loadtest.js
```

The `Host` header routes traffic to the dev environment through the shared ingress.

### 3. Observe (alert thresholds are the same as production rules)

| Signal | Observed during the drill |
| :--- | :--- |
| 5xx error rate | **22.2%** (injected 25% minus non-faulted routes) |
| p95 latency | **1.91 s** (crosses the 1 s `HighLatency` threshold) |
| Queue backlog | ~2,000 orders (worker consumes slower than 25 RPS intake) |
| Alerts | `QueueBacklog` **FIRING**, `HighErrorRate` **FIRING** after its 5 m window, `HighLatency` firing per route |

### 4. Recover by reverting the commit

```bash
git revert --no-edit <chaos-commit> && git push origin main
# ArgoCD reconciles: CHAOS_ERROR_RATE back to 0, rolling update completes
```

### 5. Verify recovery

| Signal | After revert |
| :--- | :--- |
| 5xx rate | **0.0%** |
| `HighErrorRate` | resolved (removed from Alertmanager) |
| `QueueBacklog` | still firing while the backlog drains, then resolves |
| ArgoCD | **Synced / Healthy** on the revert revision |

## Evidence

<img src="/screenshots/Q8-chaos-rca/C8-alertmanager-firing.png" alt="Alertmanager firing" width="440">
<img src="/screenshots/Q8-chaos-rca/C8-grafana-5xx-spike.png" alt="5xx spike" width="440">
<img src="/screenshots/Q8-chaos-rca/C9-grafana-recovery.png" alt="Grafana recovery" width="440">
<img src="/screenshots/Q8-chaos-rca/C9-alerts-resolving.png" alt="Alerts resolving" width="440">

k6 summary (full metrics in `k6-chaos-run-results.txt`): `http_req_failed 25.16%` — matching the injected rate exactly; 1,436 orders created at 2.39/s; thresholds crossed as designed.

## Gate

The incident lifecycle is fully observable and fully reversible through commits alone — no `kubectl exec`, no manual env edits, no dashboard clicks to change configuration.

Next: [Phase 8 — Teardown & Cost](/deploy/08-teardown-and-cost).

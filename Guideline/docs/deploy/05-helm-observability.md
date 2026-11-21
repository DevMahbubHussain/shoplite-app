# Phase 5: Helm & Observability Stack

## What

The unified `helm/shoplite` chart deployed into the cluster, plus the full observability stack: kube-prometheus-stack (Prometheus, Grafana, Alertmanager), Loki + Promtail, and Tempo — with Golden Signals dashboards, the five production alert rules, and `trace_id` log↔trace correlation wired end to end.

## Why

Helm is the single packaging unit for all workloads (Deployments, StatefulSet+PVC, Services, Ingress, NetworkPolicy, HPA, PDB, Secrets, ServiceMonitors). The observability stack is what makes the later chaos drill diagnosable: alerts fire from real PromQL, dashboards show real golden signals, and Loki's derived field links a JSON log line's `trace_id` straight to its Tempo trace.

## How

```bash
# 1. Application chart (namespace: shoplite)
helm upgrade --install shoplite helm/shoplite -n shoplite --create-namespace

# 2. Observability (namespace: monitoring) — CRDs must exist before app ServiceMonitors,
#    so kube-prometheus-stack installs first
helm upgrade --install prometheus prometheus-community/kube-prometheus-stack \
  -n monitoring --create-namespace -f monitoring/kube-prometheus-stack-values.yaml

helm upgrade --install loki grafana/loki -n monitoring -f monitoring/loki-values.yaml
helm upgrade --install promtail grafana/promtail -n monitoring -f monitoring/promtail-values.yaml
helm upgrade --install tempo grafana/tempo -n monitoring -f monitoring/tempo-values.yaml

# 3. Golden Signals dashboard + the 5 production alert rules
kubectl apply -f monitoring/dashboards/dashboard-configmap.yaml
kubectl apply -f monitoring/alert-rules/alerts.yaml

# 4. UI access (port-forward)
kubectl port-forward svc/prometheus-grafana -n monitoring 3000:80 &
kubectl port-forward svc/prometheus-kube-prometheus-prometheus -n monitoring 9090:9090 &
kubectl port-forward svc/prometheus-kube-prometheus-alertmanager -n monitoring 9093:9093 &
kubectl port-forward svc/argocd-server -n argocd 8888:80 &
```

Grafana login: `admin` / value of `grafana.adminPassword` in the stack values. Verify scraping:

```bash
curl -s http://localhost:9090/api/v1/targets | grep -c shoplite   # app targets up
curl -s http://localhost:9090/api/v1/rules  | grep shoplite-alerts # 5 custom rules loaded
```

## Configuration lessons captured in this run

| Issue | Root cause | Fix |
| :--- | :--- | :--- |
| Web pod CrashLoop | nginx upstream name `catalog-api` unresolvable in cluster | Helm service alias template (`catalog-api`) keeping the baked nginx config valid |
| Grafana provisioning crash | Two datasources marked default | Removed duplicate `isDefault: true` |
| Grafana panels "No data" | Datasource URL pointed at a stale release name | Corrected to `prometheus-kube-prometheus-prometheus.monitoring:9090` |
| Loki `mkdir /var/loki: read-only fs` | No writable volume | `persistence.enabled: true` (1Gi PVC) |
| Tempo same error | No writable volume for `/var/tempo` | `extraVolumes/extraVolumeMounts` (emptyDir) nested under `tempo:` |
| Scheduling failures | Node memory pressure from memcached caches | `chunksCache/resultsCache.enabled: false` for single-binary mode |

## Evidence

<img src="/screenshots/Q6-observability/C4-golden-signals.png" alt="Golden Signals" width="440">
<img src="/screenshots/Q6-observability/C5-loki-logs.png" alt="Loki logs" width="440">
<img src="/screenshots/Q6-observability/C6-loki-logs.png" alt="Loki filtered" width="440">
<img src="/screenshots/Q6-observability/C7-loki-logs.png" alt="Trace links" width="440">

## Gate

All monitoring pods `Running`; 8+ shoplite scrape targets `up`; `shoplite-alerts` group with `HighErrorRate`, `HighLatency`, `QueueBacklog`, `PodCrashLooping`, `NodeDiskFilling` loaded.

Next: [Phase 6 — GitOps with ArgoCD](/deploy/06-gitops-argocd).

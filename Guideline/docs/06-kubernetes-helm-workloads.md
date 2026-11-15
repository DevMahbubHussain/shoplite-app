# 6. Kubernetes & Helm Workloads (Question 5)

This section details how to lint the unified Helm chart, test template rendering, deploy workloads to Kubernetes, verify NetworkPolicy isolation, and check PodDisruptionBudget & HorizontalPodAutoscaler.

---

## 6.1 Helm Chart Linting & Dry-Run Template Rendering

From the repository root:

```bash
# 1. Lint the unified Helm chart
helm lint helm/shoplite
```

### Expected Output:
```text
==> Linting helm/shoplite
[INFO] Chart.yaml: icon is recommended

1 chart(s) linted, 0 chart(s) failed
```

### 2. Dry-Run Template Rendering for Dev & Prod
Verify that manifests render cleanly without syntax or scoping errors:

```bash
# Test Dev values rendering
helm template shoplite-dev helm/shoplite -f helm/shoplite/values-dev.yaml > /tmp/rendered-dev.yaml

# Test Prod values rendering
helm template shoplite-prod helm/shoplite -f helm/shoplite/values-prod.yaml > /tmp/rendered-prod.yaml
```

---

## 6.2 Deploying to a Kubernetes Cluster (Minikube / k3d / EKS / EC2)

Deploy the workloads into the isolated `shoplite` namespace:

```bash
# 1. Create the dedicated namespace
kubectl create namespace shoplite

# 2. Deploy using Helm
helm upgrade --install shoplite helm/shoplite \
  --namespace shoplite \
  -f helm/shoplite/values-dev.yaml

# 3. Watch pods until all report Running and Ready
kubectl get pods -n shoplite -w
```

### Expected Workload Pods:
- `catalog-api-*` (2/2 Ready)
- `order-worker-*` (1/1 Ready)
- `web-*` (2/2 Ready)
- `postgres-0` (StatefulSet, 1/1 Ready)
- `redis-*` (1/1 Ready)

---

## 6.3 Verifying Non-Root Pod Security Context

Verify that the pods run with strict non-root UID 10001 and dropped capabilities:

```bash
# Inspect securityContext of catalog-api
kubectl get deployment catalog-api -n shoplite -o jsonpath='{.spec.template.spec.securityContext}' | jq .

# Expected Output:
# {
#   "fsGroup": 10001,
#   "runAsGroup": 10001,
#   "runAsNonRoot": true,
#   "runAsUser": 10001
# }

# Verify container capabilities dropped
kubectl get deployment catalog-api -n shoplite -o jsonpath='{.spec.template.spec.containers[0].securityContext}' | jq .
# Expected: allowPrivilegeEscalation: false, capabilities.drop: ["ALL"]
```

---

## 6.4 Verifying NetworkPolicy Isolation

Inspect the `shoplite-network-policy` applied to PostgreSQL and Redis:

```bash
# Describe the NetworkPolicy
kubectl describe networkpolicy shoplite-network-policy -n shoplite
```

### Key Policy Rules:
1. **PostgreSQL Ingress (5432):** Only allows pods matching `app.kubernetes.io/name: catalog-api` or `app.kubernetes.io/name: order-worker`.
2. **Redis Ingress (6379):** Only allows pods matching `app.kubernetes.io/name: catalog-api` or `app.kubernetes.io/name: order-worker`.
3. **Web Pods or External Pods:** Cannot reach port 5432 or 6379 directly.

### Verification Probe:
```bash
# Spin up a temporary pod without permitted labels
kubectl run net-probe --image=curlimages/curl --rm -it --restart=Never -n shoplite -- nc -zv -w 3 postgres 5432
# Expected: Connection timed out (Blocked by NetworkPolicy).
```

---

## 6.5 Verifying PodDisruptionBudget & HPA

```bash
# 1. Check PodDisruptionBudget
kubectl get pdb -n shoplite
# Expected: catalog-api-pdb (minAvailable: 1)

# 2. Check HorizontalPodAutoscaler
kubectl get hpa -n shoplite
# Expected: order-worker-hpa (min: 1, max: 4, targetCPU: 70%)
```

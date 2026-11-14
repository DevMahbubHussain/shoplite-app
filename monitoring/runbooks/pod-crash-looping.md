# Runbook: PodCrashLooping

> **Alert Name:** `PodCrashLooping`  
> **Severity:** Critical  
> **Namespace:** `shoplite`  
> **Evaluation Window:** 10 minutes  
> **Threshold:** Container restart count rate $> 2$ restarts in 10 minutes

---

## 1. Incident Overview & Impact
- **Description:** One or more application pods (`catalog-api`, `order-worker`, `web`, `postgres`, `redis`) in the `shoplite` namespace have entered a CrashLoopBackOff cycle with multiple restarts within a 10-minute period.
- **Business Impact:** High probability of partial or complete service outage depending on which pod is crashing; reduced system capacity, 502 Bad Gateway responses, or halted order processing.
- **Probable Causes:**
  1. Chaos memory leak (`CHAOS_MEMORY_LEAK=true`) causing container process to exceed memory limits and trigger Linux kernel OOMKilled (Exit Code 137).
  2. Startup misconfiguration (e.g. invalid database connection string, missing secret, unparseable environment variable).
  3. Liveness probe failure due to unresponsive event loop or deadlock.
  4. Permission violation on read-only root filesystem (`readOnlyRootFilesystem: true` writing to unauthorized directory).

---

## 2. Step-by-Step Triage & Diagnosis

### Step 1: Identify Crashing Pods via kubectl
Query the status and restart count across the `shoplite` namespace:
```bash
kubectl get pods -n shoplite -o wide --sort-by='.status.containerStatuses[0].restartCount'
```

### Step 2: Inspect Container Termination Reason
Inspect the `Last State` of the crashing container:
```bash
# Example for order-worker:
kubectl describe pod -l app.kubernetes.io/component=order-worker -n shoplite | grep -A 8 "Last State:"
```
Look for key termination signals:
- **`Exit Code: 137` / `Reason: OOMKilled`:** Container exceeded its configured memory limit (`resources.limits.memory`).
- **`Exit Code: 1` / `Reason: Error`:** Application crashed with an unhandled exception or failed startup check.
- **`Exit Code: 143` (SIGTERM):** Liveness probe failed repeatedly, prompting kubelet to terminate the pod.

### Step 3: Inspect Pod Logs & Previous Container Logs
Inspect current logs and logs from the terminated container prior to restart:
```bash
# Current container stdout:
kubectl logs -l app.kubernetes.io/component=order-worker -n shoplite --tail=100

# Previous crashed container stdout:
kubectl logs -l app.kubernetes.io/component=order-worker -n shoplite -p --tail=100
```
If chaos memory leak is active, logs will show warnings such as:
`"Chaos memory leak injected: allocated 2MB"`

### Step 4: Inspect Memory Growth on Golden Signals Dashboard
1. Open the **ShopLite Golden Signals Dashboard** in Grafana.
2. Inspect Panel 4 (**Saturation - CPU & Memory Utilization**):
   - A straight upward 45-degree linear climb in pod memory right up to the $512\text{Mi}$ limit followed by a cliff-drop to zero confirms an active memory leak causing OOMKilled.

---

## 3. Remediation & Mitigation

### Option A: Chaos Memory Leak Active
If the memory curve demonstrates linear ascent and container termination reports `OOMKilled`:
1. Check worker environment variables in Kubernetes:
   ```bash
   kubectl get deployment shoplite-order-worker -n shoplite -o jsonpath='{.spec.template.spec.containers[0].env}'
   ```
2. Revert the commit in `shoplite-gitops` repository disabling `CHAOS_MEMORY_LEAK_MB: "0"`.
3. Allow ArgoCD to reconcile the healthy configuration. Pods will restart cleanly with stable memory consumption ($< 60\text{MB}$).

### Option B: Missing Secret / ConfigMap
If the pod crashes on startup due to database connectivity failure:
1. Verify the secret exists and contains required keys:
   ```bash
   kubectl get secret -n shoplite shoplite-secrets -o yaml
   ```
2. Confirm PostgreSQL is running and accepting connections on port 5432:
   ```bash
   kubectl get pods -l app.kubernetes.io/component=database -n shoplite
   ```

---

## 4. Resolution Verification
1. Verify all pods in `shoplite` show `STATUS: Running` with 0 new restarts:
   ```bash
   kubectl get pods -n shoplite
   ```
2. Confirm container memory stabilizes well below memory limits ($< 200\text{MB}$).
3. Verify Alertmanager reports `PodCrashLooping` as resolved.

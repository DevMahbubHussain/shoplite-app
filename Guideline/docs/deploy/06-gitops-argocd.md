# Phase 6: GitOps Delivery with ArgoCD

## What

ArgoCD installed in-cluster, the multi-source `shoplite-dev` Application applied from the `shoplite-gitops` repository, automated sync observed end to end, and **self-healing demonstrated live** by scaling a deployment to zero and watching ArgoCD restore it.

## Why

GitOps makes the cluster state a function of a git repository: every change is a commit, every commit is reconciled, and any manual drift is corrected automatically. This is the delivery model constraint for the platform — CI builds and promotes image tags into the GitOps repo; only ArgoCD touches the cluster.

## How

```bash
# 1. Install ArgoCD
helm repo add argo https://argoproj.github.io/argo-helm
helm upgrade --install argocd argo/argo-cd -n argocd --create-namespace \
  --set configs.params."server\.insecure"=true

# 2. Initial admin password
kubectl get secret argocd-initial-admin-secret -n argocd \
  -o jsonpath="{.data.password}" | base64 -d

# 3. Apply the dev Application (chart from shoplite-app@main + values from shoplite-gitops@main)
kubectl apply -f shoplite-gitops/apps/argocd-applications/shoplite-dev.yaml
```

The `shoplite-dev` Application uses the **multi-source pattern**:

```yaml
sources:
  - repoURL: https://github.com/DevMahbubHussain/shoplite-app.git   # Helm chart
    path: helm/shoplite
    helm:
      valueFiles:
        - $values/envs/dev/values.yaml
  - repoURL: https://github.com/DevMahbubHussain/shoplite-gitops.git # Values ref
    ref: values
syncPolicy:
  automated: { prune: true, selfHeal: true }
```

### Self-healing demonstration

```bash
# Inject drift: scale the dev catalog to zero (on camera)
kubectl scale deployment shoplite-dev-catalog-api -n shoplite-dev --replicas=0

# ArgoCD detects OutOfSync → reconciles → replicas restored (~80 seconds)
kubectl get deployment shoplite-dev-catalog-api -n shoplite-dev -w
```

Recorded timeline from this run: scaled to 0 at 15:50:52 — restored by ArgoCD at 15:52:11.

### GitOps environment separation

| Environment | Namespace | Sync | Ingress host |
| :--- | :--- | :--- | :--- |
| dev | `shoplite-dev` | automated + selfHeal | `shoplite-dev.local` |
| prod | (manual gate) | manual | catch-all |

Dev uses a dedicated ingress host so environments never collide on the catch-all route (the ingress-nginx admission webhook rejects overlapping hosts).

## Evidence

<img src="/screenshots/Q7-cicd-gitops/C3-argocd-self-heal.png" alt="ArgoCD self-heal" width="440">
<img src="/screenshots/Q7-cicd-gitops/self-heal-scale-trigger.png" alt="Scale trigger" width="440">

## Gate

`shoplite-dev` shows **Synced / Healthy**; after `--replicas=0`, ArgoCD restores the declared replica count without any human action.

Next: [Phase 7 — Chaos Drill & Recovery](/deploy/07-chaos-and-recovery).

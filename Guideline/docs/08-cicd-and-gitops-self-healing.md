# 8. CI/CD & ArgoCD Self-Healing (Question 7)

This section guides you through testing GitHub Actions CI & PR pipelines, setting up ArgoCD, and executing the automated self-healing demonstration.

---

## 8.1 GitHub Actions CI Pipeline Verification

The CI/CD pipeline enforces the **Golden Rule**:
- **CI Role:** Lint, unit test, build, scan images with Trivy (fail on CRITICAL), push to Amazon ECR via AWS OIDC, and update `shoplite-gitops/envs/dev/values.yaml` with the short Git commit SHA.
- **Prohibition:** CI **NEVER** runs `kubectl apply` or `helm upgrade`.
- **GitOps Role:** ArgoCD synchronizes desired state from Git to the cluster.

### Workflows in `.github/workflows/`:
1. **`ci.yaml` (Main Branch Push):**
   - Triggers on push to `main`.
   - Runs unit tests and Helm lint.
   - Builds container images and executes Trivy security scan.
   - Pushes images to Amazon ECR via AWS OIDC.
   - Handshakes with `shoplite-gitops` to promote image tags.
2. **`pr.yaml` (Pull Request Validation):**
   - Triggers on PR targeting `main`.
   - Validates code, runs tests, scans images.
   - Runs Terraform format, init, and validate.
   - Posts Terraform plan output directly as an automated comment on the Pull Request.

---

## 8.2 ArgoCD Setup & Application Declarations

Inspect declarations in `shoplite-gitops/apps/argocd-applications/`:
- **`shoplite-dev.yaml`:**
  - Target: `envs/dev/values.yaml`
  - Automated sync policy: `syncOptions: [CreateNamespace=true, Prune=true]`, `selfHeal: true`.
- **`shoplite-prod.yaml`:**
  - Target: `envs/prod/values.yaml`
  - Manual sync policy (production gate requiring human review).

### Deploying ArgoCD Applications:
```bash
# Apply the root App-of-Apps or application manifests
kubectl apply -f shoplite-gitops/apps/argocd-applications/shoplite-dev.yaml
kubectl apply -f shoplite-gitops/apps/argocd-applications/shoplite-prod.yaml
```

---

## 8.3 Executing the Live Self-Healing Demonstration

The assessment rubric requires demonstrating that ArgoCD automatically detects and repairs manual cluster drift without operator intervention:

### Step 1: Deliberately Tamper with Cluster State
In your terminal, scale the `catalog-api` deployment to 0 replicas:

```bash
kubectl scale deployment catalog-api -n shoplite --replicas=0
```

### Step 2: Observe Drift Detection (`OutOfSync`)
Query the pods and ArgoCD application status immediately:

```bash
kubectl get pods -n shoplite -l app.kubernetes.io/name=catalog-api
```
You will see pods terminating.

### Step 3: Watch ArgoCD Self-Heal the Cluster
Watch the pods within 15 seconds:

```bash
kubectl get pods -n shoplite -l app.kubernetes.io/name=catalog-api -w
```

### Expected Result:
ArgoCD detects that desired replicas in Git (`envs/dev/values.yaml`) is `2`, marks the application `OutOfSync`, and immediately triggers automated self-healing. Two new `catalog-api` pods are spun up and reach `Running (1/1)` status automatically.

::: tip Automated Verification Script
You can also run the automated self-healing check script directly:
```bash
bash shoplite-gitops/scripts/verify-self-healing.sh
```
:::

# Phase 3C Sub-Phase 4: GitOps Cross-Repository Promotion Handshake

## 1. Architectural Purpose & The Golden Rule of GitOps

In accordance with **C2 (Strict Architectural Boundaries & System Separation)** of `AGENTS.md`:

> **The Golden Rule:**
> - **GitHub Actions (CI):** Builds, tests, security-scans container images, publishes to Amazon ECR via AWS OIDC, and commits the updated image tag to `shoplite-gitops`.
> - **Absolute Prohibition:** The CI/CD pipeline MUST NEVER execute `kubectl apply`, `helm upgrade`, or any manual cluster deployment command.
> - **ArgoCD (GitOps):** Exclusively synchronizes and reconciles the desired state from `shoplite-gitops` to the Kubernetes cluster with automated self-healing.

This separation prevents CI runners from holding cluster-admin Kubernetes API credentials, reducing the blast radius of compromised CI environments to zero.

---

## 2. End-to-End Promotion Handshake Sequence

The automated delivery pipeline connects developer commits to production deployments through a decoupled GitOps bridge:

```
[Developer Push to shoplite-app main]
                  │
                  ▼
   ┌─────────────────────────────┐
   │ 1. GitHub Actions CI Pipeline│
   │   - Run pytest & linters    │
   │   - Scan with Trivy (CVEs)  │
   │   - Build multi-stage OCI   │
   │   - Push to Amazon ECR      │
   └──────────────┬──────────────┘
                  │ (Extract Short Git SHA)
                  ▼
   ┌─────────────────────────────┐
   │ 2. Cross-Repo GitOps Commit │
   │   - Checkout shoplite-gitops│
   │   - Update envs/dev/values  │
   │   - Git commit [skip ci]    │
   └──────────────┬──────────────┘
                  │ (Git Push to shoplite-gitops)
                  ▼
   ┌─────────────────────────────┐
   │ 3. ArgoCD GitOps Engine     │
   │   - Detects Git state diff  │
   │   - Reconciles K8s cluster  │
   │   - Restores desired state  │
   └─────────────────────────────┘
```

---

## 3. GitHub Actions Promotion Implementation

The `promote-gitops` job in [.github/workflows/ci.yaml](file:///.github/workflows/ci.yaml) executes automatically following the successful publication of images to Amazon ECR:

```yaml
  promote-gitops:
    name: Promote Container Images to GitOps (Dev)
    needs:
      - build-and-push
    if: github.ref == 'refs/heads/main' || github.event_name == 'workflow_dispatch'
    runs-on: ubuntu-latest
    steps:
      - name: Checkout Application Repository
        uses: actions/checkout@v4

      - name: Extract Short Git SHA
        id: vars
        run: echo "short_sha=$(git rev-parse --short HEAD)" >> $GITHUB_OUTPUT

      - name: Checkout GitOps Repository
        uses: actions/checkout@v4
        with:
          repository: DevMahbubHussain/shoplite-gitops
          token: ${{ secrets.GITOPS_REPO_PAT || github.token }}
          path: shoplite-gitops
          ref: main

      - name: Update Image Tags in Dev Values
        working-directory: shoplite-gitops
        env:
          NEW_TAG: ${{ steps.vars.outputs.short_sha }}
        run: |
          echo "Updating ShopLite microservice tags to: ${NEW_TAG}"
          if command -v yq >/dev/null 2>&1; then
            yq eval ".catalogApi.image.tag = \"${NEW_TAG}\"" -i envs/dev/values.yaml
            yq eval ".orderWorker.image.tag = \"${NEW_TAG}\"" -i envs/dev/values.yaml
            yq eval ".web.image.tag = \"${NEW_TAG}\"" -i envs/dev/values.yaml
          else
            sed -i "s/tag: .*/tag: \"${NEW_TAG}\"/g" envs/dev/values.yaml
          fi
          git diff envs/dev/values.yaml

      - name: Commit and Push to GitOps Repository
        working-directory: shoplite-gitops
        env:
          NEW_TAG: ${{ steps.vars.outputs.short_sha }}
        run: |
          git config user.name "github-actions[bot]"
          git config user.email "github-actions[bot]@users.noreply.github.com"
          git add envs/dev/values.yaml
          if git diff --staged --quiet; then
            echo "No changes in values.yaml, skipping commit."
          else
            git commit -m "deploy(dev): promote container images to ${NEW_TAG} [skip ci]"
            git push origin main
          fi
```

---

## 4. Operational Safety & Idempotency Controls

1. **Cross-Repo Authentication:**
   - Authenticates against `DevMahbubHussain/shoplite-gitops` using secret `GITOPS_REPO_PAT` with scoped repository write permissions.
2. **Loop Prevention:**
   - The commit message includes `[skip ci]`, preventing automated actions or secondary CI runners on `shoplite-gitops` from entering an infinite loop.
3. **Idempotency Guard (`git diff --staged --quiet`):**
   - If a manual trigger or duplicate workflow runs on the same Git commit, the step identifies that no values have changed and skips the commit gracefully without causing a non-zero exit code.
4. **Resilient YAML Manipulation:**
   - Uses native `yq` stream manipulation with fallback to regex `sed`, ensuring reliable updates regardless of runner environment differences.

---

## 5. Verification Checklist

- [x] Verified zero `kubectl` or `helm` commands in CI workflow.
- [x] Validated `.github/workflows/ci.yaml` YAML syntax with Python.
- [x] Handshake strictly targets `shoplite-gitops` repository `envs/dev/values.yaml`.
- [x] Commit message formatted with Conventional Commits and `[skip ci]`.

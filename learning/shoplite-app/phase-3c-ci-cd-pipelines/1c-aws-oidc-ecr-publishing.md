# Phase 3C Sub-Phase 3: AWS OIDC Federated Authentication & Amazon ECR Publishing

## 1. Architectural Purpose & Zero-Key Security Posture

In accordance with **C2 (Architectural Trust Boundaries)** and **C5 (Security & Least Privilege)** of `AGENTS.md`, production deployment pipelines must eliminate static, long-lived credentials:

1. **Elimination of Long-Lived Access Keys:** Storing static IAM access keys (`AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY`) in GitHub repository secrets exposes systems to credential theft, leakage in logs, or rotation fatigue.
2. **OpenID Connect (OIDC) Federated Identity:** By establishing an OIDC trust relationship between GitHub Actions (`token.actions.githubusercontent.com`) and AWS Identity and Access Management (IAM), GitHub Actions runners obtain short-lived, ephemeral AWS Security Token Service (STS) credentials valid only for the duration of the build.
3. **Immutable OCI Artifact Publishing:** Successfully tested and scanned container images are built, tagged with short Git commit SHAs, and published to Amazon Elastic Container Registry (ECR) repositories across `ap-southeast-1`.

---

## 2. AWS OIDC Trust Relationship & IAM Least Privilege

### IAM Role Trust Policy (AssumeRoleWithWebIdentity)
The AWS IAM Role `shoplite-github-actions-role` (Account `263303066497`) defines a trust relationship restricted strictly to the repository:

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Principal": {
        "Federated": "arn:aws:iam::263303066497:oidc-provider/token.actions.githubusercontent.com"
      },
      "Action": "sts:AssumeRoleWithWebIdentity",
      "Condition": {
        "StringEquals": {
          "token.actions.githubusercontent.com:aud": "sts.amazonaws.com"
        },
        "StringLike": {
          "token.actions.githubusercontent.com:sub": "repo:DevMahbubHussain/shoplite-app:*"
        }
      }
    }
  ]
}
```

### GitHub Actions Job Permissions
To request an OIDC JSON Web Token (JWT) from GitHub's OIDC provider, the workflow job specifies:

```yaml
permissions:
  id-token: write
  contents: read
```

---

## 3. GitHub Actions Amazon ECR Publishing Pipeline

The `build-and-push` job in [.github/workflows/ci.yaml](file:///.github/workflows/ci.yaml) executes only after all unit tests, helm lints, and Trivy CVE scans succeed:

```yaml
  build-and-push:
    name: Build & Push Images to Amazon ECR
    needs:
      - security-scan
    if: github.ref == 'refs/heads/main' || github.event_name == 'workflow_dispatch'
    runs-on: ubuntu-latest
    permissions:
      id-token: write
      contents: read
    strategy:
      fail-fast: false
      matrix:
        service:
          - name: catalog-api
            repo: shoplite-catalog-api
            context: services/catalog-api
          - name: order-worker
            repo: shoplite-order-worker
            context: services/order-worker
          - name: web
            repo: shoplite-web
            context: services/web
    steps:
      - name: Checkout Code
        uses: actions/checkout@v4

      - name: Set up Docker Buildx
        uses: docker/setup-buildx-action@v3

      - name: Configure AWS Credentials (OIDC)
        uses: aws-actions/configure-aws-credentials@v4
        with:
          role-to-assume: ${{ secrets.AWS_ROLE_ARN || 'arn:aws:iam::263303066497:role/shoplite-github-actions-role' }}
          aws-region: ${{ vars.AWS_REGION || 'ap-southeast-1' }}
          role-session-name: shoplite-ecr-publish

      - name: Log in to Amazon ECR
        id: login-ecr
        uses: aws-actions/amazon-ecr-login@v2

      - name: Extract Short Git SHA
        id: vars
        run: echo "short_sha=$(git rev-parse --short HEAD)" >> $GITHUB_OUTPUT

      - name: Build and Push Container Image to ECR
        uses: docker/build-push-action@v5
        with:
          context: ${{ matrix.service.context }}
          push: true
          tags: |
            ${{ steps.login-ecr.outputs.registry }}/${{ matrix.service.repo }}:${{ steps.vars.outputs.short_sha }}
            ${{ steps.login-ecr.outputs.registry }}/${{ matrix.service.repo }}:${{ github.sha }}
            ${{ steps.login-ecr.outputs.registry }}/${{ matrix.service.repo }}:latest
          cache-from: type=gha
          cache-to: type=gha,mode=max
```

---

## 4. Image Tagging & ECR Lifecycle Retention Alignment

1. **Tagging Strategy:**
   - `${{ steps.vars.outputs.short_sha }}`: Short 7-character Git commit hash (e.g., `90d0f78`), providing human-readable, deterministic references for Helm values files.
   - `${{ github.sha }}`: Full 40-character immutable commit identifier for auditability.
   - `latest`: Rolling pointer to the most recent successful build on `main`.
2. **ECR Lifecycle Policy Compliance:**
   - Configured via Terraform module `modules/ecr/main.tf`.
   - Untagged images expire after 14 days.
   - Tagged images retain the last 10 versions matching prefixes `["v", "sha", "release", "build"]` or git commit hashes, preventing unbounded registry storage costs.

---

## 5. Verification Checklist

- [x] Validated YAML structure with Python `yaml.safe_load`.
- [x] OIDC action configured with `aws-actions/configure-aws-credentials@v4` targeting region `ap-southeast-1`.
- [x] ECR login configured with official `aws-actions/amazon-ecr-login@v2`.
- [x] Container tagging tags both short SHA, full SHA, and latest.
- [x] Multi-stage caching configured with `type=gha`.

# ShopLite Manual CLI Testing & Verification Master Guide

This standalone document provides a complete, step-by-step CLI testing guide for the ShopLite cloud-native microservices e-commerce platform. It is designed to be executed manually from scratch in your terminal.

---

## Table of Contents
1. [Prerequisites & CLI Setup](#1-prerequisites--cli-setup)
2. [Module Q1: Application Source Code & Unit Tests](#2-module-q1-application-source-code--unit-tests)
3. [Module Q2: Docker Containerization & Smoke Testing](#3-module-q2-docker-containerization--smoke-testing)
4. [Module Q3: Linux Hardening & Backup Automation](#4-module-q3-linux-hardening--backup-automation)
5. [Module Q4: AWS Terraform IaC & Ansible](#5-module-q4-aws-terraform-iac--ansible)
6. [Module Q5: Kubernetes Workloads & Helm Packaging](#6-module-q5-kubernetes-workloads--helm-packaging)
7. [Module Q6: Unified Observability Stack](#7-module-q6-unified-observability-stack)
8. [Module Q7: CI/CD Pipeline & ArgoCD Self-Healing](#8-module-q7-cicd-pipeline--argocd-self-healing)
9. [Module Q8: Chaos Engineering & RCA Incident Post-Mortem](#9-module-q8-chaos-engineering--rca-incident-post-mortem)
10. [Submission Evidence & Screenshot Checklist](#10-submission-evidence--screenshot-checklist)

---

## 1. Prerequisites & CLI Setup

### 1.1 Virtual Environment
```bash
python -m venv .venv
source .venv/bin/activate       # On Linux / macOS
.\.venv\Scripts\Activate.ps1    # On Windows PowerShell

pip install -r services/catalog-api/requirements.txt
pip install -r services/order-worker/requirements.txt
pip install pytest pytest-asyncio
```

### 1.2 Configuration
```bash
cp .env.example .env
```

---

## 2. Module Q1: Application Source Code & Unit Tests

### 2.1 Run Automated Unit Tests (29 Passed)
```bash
pytest services/catalog-api/tests services/order-worker/tests -v
```

### 2.2 Manually Test All 7 Endpoints via curl
```bash
# Health & Readiness Probes
curl -i http://localhost:8000/healthz
curl -i http://localhost:8000/readyz

# Product Catalog
curl -s http://localhost:8000/products | jq .
curl -i http://localhost:8000/products/1
curl -i http://localhost:8000/products/9999

# Place Order & Query Status
curl -i -X POST http://localhost:8000/orders \
  -H "Content-Type: application/json" \
  -d '{"product_id": 1, "quantity": 2}'

curl -s http://localhost:8000/orders/1 | jq .

# Prometheus Metrics
curl -s http://localhost:8000/metrics | grep http_requests_total
```

### 2.3 Inspect Database & Cache Directly
```bash
# Direct PostgreSQL inspection
docker compose exec postgres psql -U shoplite -d shoplite_db -c "SELECT id, name, price, stock FROM products LIMIT 5;"
docker compose exec postgres psql -U shoplite -d shoplite_db -c "SELECT * FROM orders ORDER BY id DESC LIMIT 5;"

# Direct Redis queue inspection
docker compose exec redis redis-cli LLEN orders:pending
docker compose exec redis redis-cli LLEN orders:processing
```

---

## 3. Module Q2: Docker Containerization & Smoke Testing

### 3.1 Build & Inspect Image Sizes (<150 MB Rule)
```bash
docker compose build
docker images | grep -E "(shoplite|web|catalog-api|order-worker)"
```
- `shoplite-web`: < 45 MB (Non-root `appuser`, UID 10001)
- `shoplite-catalog-api`: < 120 MB (Non-root `appuser`, UID 10001)
- `shoplite-order-worker`: < 110 MB (Non-root `appuser`, UID 10001)

### 3.2 Run the End-to-End Smoke Test
```bash
# Start the full stack
docker compose up -d

# Execute smoke test script
bash scripts/smoke-test.sh
# Or PowerShell: .\scripts\smoke-test.ps1
```

---

## 4. Module Q3: Linux Hardening & Backup Automation

```bash
# 1. Verify SSH Hardening
sshd -T | grep -E "(permitrootlogin|passwordauthentication|pubkeyauthentication)"

# 2. Verify Directory Permissions and single ACL rule
ls -ld /var/log/shoplite
getfacl /var/log/shoplite

# 3. Verify Backup Timer & Service
systemctl status shoplite-backup.timer
systemctl list-timers --all | grep shoplite-backup
sudo systemctl start shoplite-backup.service
systemctl status shoplite-backup.service

# 4. Verify UFW Firewall Status
sudo ufw status verbose
ss -tulpn
```

---

## 5. Module Q4: AWS Terraform IaC & Ansible

```bash
cd terraform

# Validate HCL Syntax
terraform fmt -check
terraform init -backend=false
terraform validate

# Simulate Plan (with AWS credentials or mock)
terraform plan

# Ansible Playbooks Syntax Check
cd ../ansible
ansible-playbook --syntax-check playbooks/harden.yml
ansible-playbook --syntax-check playbooks/containerd.yml
ansible-playbook --syntax-check playbooks/k8s-cluster.yml
ansible-playbook --syntax-check playbooks/fetch-kubeconfig.yml
```

---

## 6. Module Q5: Kubernetes Workloads & Helm Packaging

```bash
# 1. Lint the Helm chart
helm lint helm/shoplite

# 2. Dry-Run Template Rendering
helm template test-dev helm/shoplite -f helm/shoplite/values-dev.yaml
helm template test-prod helm/shoplite -f helm/shoplite/values-prod.yaml

# 3. Deploy to Cluster
helm upgrade --install shoplite helm/shoplite -n shoplite --create-namespace -f helm/shoplite/values-dev.yaml

# 4. Inspect Workloads, SecurityContext, NetworkPolicy, PDB, and HPA
kubectl get pods,svc,pdb,hpa -n shoplite
kubectl describe networkpolicy shoplite-network-policy -n shoplite
```

---

## 7. Module Q6: Unified Observability Stack

```bash
# Deploy Observability (Prometheus, Loki, Tempo, Promtail)
bash monitoring/install-observability.sh

# Port-forward Grafana
kubectl port-forward svc/prometheus-grafana 3000:80 -n monitoring
```
- Open `http://localhost:3000` $\to$ Golden Signals Dashboard.
- Loki: `{service="catalog-api"} | json` $\to$ Click blue `trace_id` link $\to$ Opens distributed trace flame graph in Tempo.
- Alertmanager: verify all 5 alerts in `monitoring/alert-rules/alerts.yaml`.

---

## 8. Module Q7: CI/CD Pipeline & ArgoCD Self-Healing

### Self-Healing Demonstration:
```bash
# 1. Scale catalog-api to 0 replicas
kubectl scale deployment catalog-api -n shoplite --replicas=0

# 2. Watch ArgoCD detect drift (OutOfSync) and restore 2 replicas within 15 seconds
kubectl get pods -n shoplite -w
```

---

## 9. Module Q8: Chaos Engineering & RCA Incident Post-Mortem

```bash
# 1. Run 25 VU load test (>= 20 RPS)
k6 run --vus 25 --duration 15m loadtest.js

# 2. Apply chaos overlay in shoplite-gitops/envs/prod/values.yaml
# 3. Observe alert firing in Alertmanager -> Loki 500 error logs -> Tempo trace span
# 4. Revert Git commit in shoplite-gitops -> ArgoCD auto-syncs clean state
# 5. Read RCA report: docs/RCA/RCA_REPORT.md
```

---

## 10. Submission Evidence & Screenshot Checklist

| Checkpoint | Command / UI Screen | Output Verified |
| :--- | :--- | :--- |
| **1. Unit Tests** | `pytest services/` | 29 passed |
| **2. Smoke Test** | `bash scripts/smoke-test.sh` | 5/5 steps pass cleanly |
| **3. Docker Sizes** | `docker images` | All 3 images < 150 MB, non-root UID 10001 |
| **4. SSH Hardening** | `sshd -T` | `permitrootlogin no`, `passwordauthentication no` |
| **5. ACL Permissions** | `getfacl /var/log/shoplite` | Mode 750, single ACL rule `g:ops:r-X` |
| **6. Backup Timer** | `systemctl list-timers` | Active, scheduled 02:00:00 UTC |
| **7. UFW Firewall** | `sudo ufw status verbose` | Default deny, only 22, 80, 443 allowed |
| **8. Terraform Plan** | `terraform validate && plan` | Success, zero errors |
| **9. K8s Workloads** | `kubectl get pods -n shoplite` | All running non-root |
| **10. Golden Signals** | Grafana Dashboard UI | RPS, p50/p95/p99 latency, 5xx rate, queue depth |
| **11. Trace Link** | Grafana Loki $\to$ Tempo UI | `trace_id` derived field navigation |
| **12. Fired Alert** | Alertmanager UI | `HighErrorRate` or `HighLatency` active |
| **13. CI/CD Run** | GitHub Actions UI | Green pipeline with Trivy scan and OIDC |
| **14. Self-Healing** | ArgoCD UI / Terminal | Pod restore after manual scale down |
| **15. RCA Report** | `docs/RCA/RCA_REPORT.md` | Formal 1–2 page post-mortem |

# 10. Required Evidence & Screenshot Checklist

This checklist details every specific screenshot, terminal output log, and document required for final submission and evaluation according to Section 2.2 of the specification.

---

## 10.1 Required Screenshots Matrix

Capture clear, full-window screenshots and store them under the corresponding documentation folders:

| Item # | Checkpoint Description | Tool / Screen to Capture | Expected Evidence in Screenshot | Target Path |
| :---: | :--- | :--- | :--- | :--- |
| **SS-01** | **Passing Unit Tests** | Terminal | Output of `pytest services/` showing 29 passed tests. | `docs/evidence/01-unit-tests.png` |
| **SS-02** | **Smoke Test Execution** | Terminal | Output of `bash scripts/smoke-test.sh` showing all 5 steps passing. | `docs/evidence/02-smoke-test.png` |
| **SS-03** | **Non-Root Docker Build** | Terminal | Output of `docker images` showing sizes < 150MB and `id` showing UID 10001. | `docs/evidence/03-docker-sizes.png` |
| **SS-04** | **SSH Hardening & Failed Login** | Terminal | Output of `sshd -T` and `ssh` rejecting password authentication. | `linux/evidence/04-sshd-config.png` |
| **SS-05** | **ACL & Directory Permissions** | Terminal | Output of `ls -ld /var/log/shoplite` and `getfacl /var/log/shoplite`. | `linux/evidence/05-log-acl.png` |
| **SS-06** | **Systemd Backup Timer** | Terminal | Output of `systemctl list-timers` and `systemctl status shoplite-backup.service`. | `linux/evidence/06-backup-timer.png` |
| **SS-07** | **UFW Firewall Status** | Terminal | Output of `sudo ufw status verbose` showing only 22, 80, 443 allowed. | `linux/evidence/07-ufw-firewall.png` |
| **SS-08** | **Terraform Plan & Validation** | Terminal | Output of `terraform validate` and `terraform plan` execution. | `docs/evidence/08-terraform-plan.png` |
| **SS-09** | **Kubernetes Workload Pods** | Terminal / Lens | Output of `kubectl get pods,svc,pdb,hpa -n shoplite`. | `docs/evidence/09-k8s-workloads.png` |
| **SS-10** | **Golden Signals Dashboard** | Grafana UI | Traffic, Latency p50/p95/p99, Error 5xx rate, Queue Backlog under load. | `docs/evidence/10-golden-signals.png` |
| **SS-11** | **Loki Logs to Tempo Trace Link**| Grafana UI | Split-screen showing Loki log entry with Derived Field linking to Tempo trace. | `docs/evidence/11-trace-correlation.png` |
| **SS-12** | **Fired Alertmanager Alert** | Alertmanager UI | `HighErrorRate` or `HighLatency` alert in active/firing state. | `docs/evidence/12-alertmanager.png` |
| **SS-13** | **CI/CD Pipeline Run** | GitHub Actions | Completed pipeline run with green checks on Tests, Lint, Trivy, and ECR publish. | `docs/evidence/13-github-actions.png` |
| **SS-14** | **ArgoCD Self-Healing** | ArgoCD UI / CLI | ArgoCD restoring `catalog-api` back to 2 replicas after deliberate scale to 0. | `docs/evidence/14-argocd-self-heal.png` |

---

## 10.2 Deliverable Files Verification Checklist

Ensure the following critical files exist in your repositories before final submission:

### Application Repository (`shoplite-app`):
- [x] **Architecture Diagram:** `docs/architecture-diagram/shoplite-system-architecture.svg` and markdown specs.
- [x] **Application Code & Tests:** `services/catalog-api/`, `services/order-worker/`, `services/web/`.
- [x] **Containerization:** `services/*/Dockerfile`, `docker-compose.yml`, `.dockerignore`.
- [x] **Smoke Test & Makefile:** `scripts/smoke-test.sh`, `scripts/smoke-test.ps1`, `Makefile`.
- [x] **Linux Configuration & Evidence:** `linux/sshd_config`, `linux/systemd/`, `linux/firewall/`, `linux/evidence/verification-evidence.md`.
- [x] **Terraform & Ansible:** `terraform/modules/` (network, compute, alb, ecr), `terraform/main.tf`, `ansible/playbooks/`.
- [x] **Helm Workloads:** `helm/shoplite/` (templates for Deployment, StatefulSet, NetworkPolicy, PDB, HPA, ServiceMonitors).
- [x] **Observability Stack:** `monitoring/kube-prometheus-stack-values.yaml`, `monitoring/loki-values.yaml`, `monitoring/tempo-values.yaml`, `monitoring/dashboards/golden-signals.json`, `monitoring/alert-rules/alerts.yaml`, `monitoring/runbooks/` (5 runbooks).
- [x] **CI Workflows:** `.github/workflows/ci.yaml`, `.github/workflows/pr.yaml`.
- [x] **Load Testing Script:** `loadtest.js`, `scripts/loadtest.js`.
- [x] **Root Cause Analysis (RCA):** `docs/RCA/RCA_REPORT.md`, `docs/RCA/RCA_INCIDENT_REPORT.md`.

### GitOps Repository (`shoplite-gitops`):
- [x] **ArgoCD Applications:** `apps/argocd-applications/shoplite-dev.yaml`, `shoplite-prod.yaml`, `app-of-apps.yaml`.
- [x] **Environment Values:** `envs/dev/values.yaml`, `envs/prod/values.yaml`.
- [x] **Chaos Overlays & Playbook:** `chaos/overlays/` (4 flag overlays), `chaos/chaos-exercise-playbook.md`.
- [x] **Self-Healing Script:** `scripts/verify-self-healing.sh`.

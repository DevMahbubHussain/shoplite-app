---
layout: home

hero:
  name: "ShopLite Verification Guide"
  text: "100% Manual CLI Testing & Evidence Protocol"
  tagline: "Step-by-step CLI runbook covering all 8 modules from scratch — no agents, pure terminal commands."
  actions:
    - theme: brand
      text: Start Testing From Scratch
      link: /01-prerequisites-and-local-env
    - theme: alt
      text: Evidence Checklist
      link: /10-evidence-and-screenshot-checklist

features:
  - title: 🚀 Fast Local Verification
    details: Run unit tests (29 passed), Docker Compose multi-stage builds (<150MB, non-root UID 10001), and smoke tests.
  - title: 🔒 OS Hardening & Cloud IaC
    details: Test Linux ACLs (750 mode), SSH lockdown, systemd backup timers, Terraform VPC (2 AZs), and Ansible playbooks.
  - title: ☸️ Kubernetes & GitOps
    details: Validate Helm chart linting, NetworkPolicy isolation, PDB, HPA, and demonstrate ArgoCD automated self-healing.
  - title: 📈 Unified Observability & Chaos
    details: Inspect Prometheus metrics, Loki logs, Tempo traces, fire 5 Alertmanager alerts, and document post-mortem RCA.
---

## Assessment Modules & Verification Roadmap

| Module | Scope & Deliverable | Manual Verification Command | Pass Criteria |
| :--- | :--- | :--- | :--- |
| **Q1: API & Worker** | FastAPI 7 routes, Redis list queue, auto-seeding | `pytest services/` | 29/29 tests pass |
| **Q2: Containerization** | Multi-stage Docker, Compose stack, non-root UID 10001 | `bash scripts/smoke-test.sh` | All 5 steps pass cleanly |
| **Q3: Linux Hardening** | SSH key-only, mode 750 + ACL, backup timer, UFW | `sshd -T`, `getfacl`, `systemctl` | Restricted ports & permissions |
| **Q4: AWS IaC & Ansible** | Modular VPC (2 AZs), ALB, ECR, S3 state backend | `terraform validate && terraform plan` | Valid HCL, zero plan errors |
| **Q5: Helm & K8s** | Unified chart, NetworkPolicy, PDB, HPA, SecurityContext | `helm lint helm/shoplite` | 0 chart errors, valid templates |
| **Q6: Observability** | Prometheus, Loki, Tempo, Golden Signals, 5 Alerts | `curl -s localhost:8000/metrics` | Correlated metrics, logs & traces |
| **Q7: CI/CD & GitOps** | GitHub Actions workflows, ArgoCD apps & self-healing | `kubectl scale deployment catalog-api --replicas=0` | ArgoCD restores state automatically |
| **Q8: Chaos & RCA** | k6 load generator (25 VUs, $\ge 20$ RPS), RCA post-mortem | `k6 run loadtest.js` | Alert fires $\to$ Loki $\to$ Tempo $\to$ Git revert |

::: tip Manual Testing Philosophy
Every command in this guide is designed to be executed directly in your local terminal (bash/PowerShell/zsh). You will inspect real HTTP response codes, query PostgreSQL and Redis directly via CLI, validate manifests, run load tests, and capture required evidence.
:::

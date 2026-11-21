# Live Deployment Walkthrough — Overview

This section documents the complete **live deployment exercise** executed on 2026-11-21: taking the ShopLite platform from source code to a running, observable, GitOps-managed Kubernetes cluster on a local workstation — including a full chaos-injection and recovery drill.

Every page follows the same structure: **What** was built, **Why** it matters operationally, **How** to reproduce it (exact commands), the **Endpoints** exposed, and the **Evidence** captured at each gate.

## Toolchain

| Tool | Version | Role |
| :--- | :--- | :--- |
| Docker Desktop | WSL2 backend, Engine 29.9.3 | Image builds, Compose stack, kind node runtime |
| Docker Compose | v2 | Local 5-service orchestration |
| Terraform | 1.13.2 | Cloud infrastructure definition + read-only plan validation |
| kubectl | 1.34.1 | Cluster administration |
| Helm | 4.3.1 | Application + observability chart deployment |
| kind | v2.4.0 (kind binary) | Local Kubernetes 1.37 control plane |
| Ansible | core 2.21.6 (WSL) | OS hardening + cluster bootstrap automation |
| k6 | v2.4.0 | Load generation (25 VUs) |
| Prometheus / Grafana / Loki / Tempo | kube-prometheus-stack + grafana charts | Metrics, dashboards, logs, traces |
| ArgoCD | stable Helm chart | GitOps reconciliation + self-healing |

## Deployment Phases

| Phase | Outcome | Evidence Folder |
| :--- | :--- | :--- |
| 1. Local Compose Stack | 5 services healthy, full order lifecycle | `Q1-api-application`, `Q2-containerization` |
| 2. Linux Hardening (WSL) | sshd, ACLs, UFW, backup timer verified | `Q3-linux-hardening` |
| 3. Terraform Plan | 37-resource cloud plan validated (read-only) | `Q4-aws-iac` |
| 4. Kind Cluster | Kubernetes 1.37 Ready + images loaded | `Q5-kubernetes-helm` |
| 5. Helm & Observability | App chart + Prometheus/Grafana/Loki/Tempo green | `Q6-observability` |
| 6. GitOps with ArgoCD | Synced/Healthy + self-healing demonstrated | `Q7-cicd-gitops` |
| 7. Chaos Drill & Recovery | Fault → alerts → revert → verified recovery | `Q8-chaos-rca` |
| 8. Teardown & Cost | Clean removal + cost model | — |

## Runtime Endpoints (local cluster)

| Endpoint | URL |
| :--- | :--- |
| Web UI (ingress path `/`) | `http://localhost:30080/` |
| API via ingress | `http://localhost:30080/api/products` |
| Dev environment (Host header) | `http://localhost:30080/api` + `Host: shoplite-dev.local` |
| Grafana | `http://localhost:3000` (port-forward) |
| Prometheus | `http://localhost:9090` (port-forward) |
| Alertmanager | `http://localhost:9093` (port-forward) |
| ArgoCD UI | `http://localhost:8888` (port-forward) |

Get started with [Phase 1: Local Compose Stack](/deploy/01-local-compose-stack).

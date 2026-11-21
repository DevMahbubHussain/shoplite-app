# ShopLite — Deliverable Evidence Index

**Verification date:** 2026-11-21
**Scope:** Consolidated map of every required deliverable to its on-disk artifact, the command that verifies it, and the results of the verification suite executed on this date.

---

## 1. Verification Results (2026-11-21)

| # | Gate | Command | Result |
| :--- | :--- | :--- | :--- |
| 1 | Terraform configuration | `terraform -chdir=terraform validate` | **Success — configuration is valid** |
| 2 | Helm chart lint | `helm lint helm/shoplite` | **1 chart linted, 0 failed** |
| 3 | Helm render (full manifest set) | `helm template shoplite helm/shoplite \| grep -c "^kind:"` | **23 resources render cleanly** |
| 4 | Docker Compose schema | `docker compose config --quiet` | **VALID** |
| 5 | Smoke-test script syntax | `bash -n scripts/smoke-test.sh` | **SYNTAX OK** |
| 6 | Ansible playbooks (×4) | `ansible-playbook <pb> --syntax-check` | **All 4: SYNTAX OK** (harden, containerd, k8s-cluster, fetch-kubeconfig) |
| 7 | Unit test suite (API + worker) | `python -m pytest -q` | **29 passed in 10.11s** |

---

## 2. Deliverable → Artifact Matrix

| Required deliverable | Artifact location | Evidence form | Status |
| :--- | :--- | :--- | :--- |
| Architecture diagram | `docs/architecture-diagram/` — full system architecture, API low-level design, use-case & sequence diagrams, `shoplite-system-architecture.svg` | Diagrams + HTML viewer (`index.html`) | Complete |
| Application source code | `services/catalog-api/app/`, `services/order-worker/worker/`, `services/web/src/` | Layered OOP codebase (routers → services → repositories), typed Pydantic DTOs | Complete |
| Unit tests | `services/catalog-api/tests/test_api.py`, `services/order-worker/tests/` | 29 tests: API contract, worker state transitions, queue recovery sweep, graceful shutdown | Complete |
| Dockerfiles + Compose | `services/*/Dockerfile` (multi-stage, non-root UID 10001), `docker-compose.yml` (5 services) | Images < 150 MB; compose health-gated | Complete |
| Smoke-test script + Makefile | `scripts/smoke-test.sh`, `Makefile` | End-to-end probe: readyz → seeds ≥10 → order → poll COMPLETED | Complete |
| Linux configuration + terminal evidence | `linux/sshd_config`, `linux/systemd/`, `linux/firewall/`, **`linux/evidence/verification-evidence.md`** | Terminal outputs: `sshd -T`, `getfacl`, `systemctl status shoplite-backup.timer`, `ufw status verbose` | Complete |
| Terraform modules | `terraform/modules/{network,compute,alb,ecr}/` + `bootstrap/` + remote S3/DynamoDB backend | 2-AZ VPC, private-subnet compute with SSM-only access, ALB → NodePorts, ECR ×3, budget alarm | Complete |
| Ansible playbooks | `ansible/playbooks/{harden,containerd,k8s-cluster,fetch-kubeconfig}.yml` | OS hardening, containerd, kubeadm v1.29 + Calico v3.27, kubeconfig retrieval | Complete |
| Kubernetes manifests / Helm chart | `helm/shoplite/` — 18 templates incl. NetworkPolicy, HPA (worker 1–4), PDB, StatefulSet + PVC, Secret/ConfigMap, ServiceMonitors | Chart lints clean; 23 resources | Complete |
| Monitoring dashboards | `monitoring/dashboards/golden-signals.json`, `dashboard-configmap.yaml` | Golden Signals as code: RPS, p50/95/99, 5xx, pod CPU/mem, queue depth, orders created vs processed | Complete |
| Alert rules + runbooks | `monitoring/alert-rules/alerts.yaml`, `alertmanager-config.yaml`, `monitoring/runbooks/*.md` (all 5) | HighErrorRate, HighLatency, QueueBacklog, PodCrashLooping, NodeDiskFilling — each with severity + runbook_url | Complete |
| CI/CD workflows | `.github/workflows/ci.yaml`, `pr.yaml` | Lint (hadolint/helm/python), tests, Trivy CRITICAL gate, ECR push via OIDC, GitOps tag promotion — zero kubectl in CI | Complete |
| GitOps configuration | `shoplite-gitops/` — ArgoCD apps + `envs/{dev,prod}/values.yaml` | Auto-sync dev, manual prod, self-heal | Complete |
| Chaos exercise + RCA | `loadtest.js` (k6), **`docs/RCA/RCA_REPORT.md`** + `RCA_INCIDENT_REPORT.md` | Formal post-mortem: 13-min Sev-1 incident, observability-only diagnosis chain, GitOps revert, MTTR 8 min | Complete |
| Deployment process record | `docs/deployment/AWS_LIVE_DEPLOYMENT.md` | Full live-AWS runbook: real infra values, SSM transport, incident log, teardown protocol | Complete (commit `3665a94`) |

---

## 3. Live-Runtime Evidence — Status and Substitutions

The managed sandbox account used for cloud deployments applies an account-wide policy that blocks SSM execution channels (RunCommand and Session Manager dead; heartbeat unaffected), so no new live-cluster screenshots can be captured on that environment.

Existing artifacts already capture the live-runtime behavior in verifiable form:

1. **Chaos / RCA exercise (executed 2026-11-15 on a live cluster):** `docs/RCA/RCA_REPORT.md` records the complete evidence chain with concrete telemetry — 20.4% 5xx on `POST /orders` at 25 RPS (k6), p95 1,520 ms, PromQL for every alert, structured Loki log lines with `trace_id`, Tempo span hierarchy, and the ArgoCD revert-to-green timeline. This is the strongest available proof of the running stack's observability behavior.
2. **Golden Signals dashboard as code:** `monitoring/dashboards/golden-signals.json` renders every required panel; import into Grafana to view live.
3. **Linux hardening terminal evidence:** `linux/evidence/verification-evidence.md` contains per-checkpoint command outputs (`sshd -T`, ACLs, systemd timer, UFW).
4. **Live AWS infrastructure record:** `docs/deployment/AWS_LIVE_DEPLOYMENT.md` documents a complete apply cycle (VPC, 3× EC2, ALB, ECR) with actual resource IDs, ALB DNS, and outputs from the 2026-11-21 deployment.

**Regenerating live runtime screenshots (local stack):**

```bash
make build && make up && make smoke     # full working stack + end-to-end probe
# Grafana/Prometheus from the monitoring stack: kubectl port-forward or
# docker-compose profile per monitoring/install-observability.sh
```

---

## 4. Screenshot Evidence Manifest (by assessment question)

All captures live under `docs/evidence/screenshots/`, organized per assessment question. The main `README.md` embeds the same gallery under descriptive section titles.

| Question | Directory | Files | Demonstrates |
| :--- | :--- | :--- | :--- |
| **Q1 — API & Order Processing** | `Q1-api-application/` | `web-ui-catalog.png`, `health-readiness-probes.png`, `products-listing.png`, `order-creation-201.png`, `order-lifecycle-completed.png`, `structured-json-logs.png`, `prometheus-metrics.png` | All 7 endpoints live, ≥10 seeded products, 201 order creation, async lifecycle to `COMPLETED`, JSON logs with `trace_id`, metrics exposition |
| **Q2 — Containerization** | `Q2-containerization/` | `compose-services-healthy.png`, `image-sizes-under-150mb.png`, `nonroot-uid-10001.png` | 5 healthy services, images 145/141/112 MB (<150 MB gate), non-root UID 10001 |
| **Q3 — Linux Hardening** | `Q3-linux-hardening/` | `B2-log-dir-acl.png`, `B3-backup-timer.png`, `B4-ufw-firewall.png`, `B5-open-ports.png`, `B6-users-groups.png` | `/var/log/shoplite` 750 + ACL, backup timer active, UFW default-deny with 22/80/443, listeners, deploy/ops accounts (`sshd -T` values additionally in `linux/evidence/verification-evidence.md`) |
| **Q4 — AWS IaC** | `Q4-aws-iac/` | `D1-terraform-plan.png`, `D2-plan-summary.png` | Read-only `terraform plan`: 37 resources (VPC, subnets, EC2, ALB, ECR); full plan text at `terraform-plan-2026-11-21.txt` |
| **Q5 — Kubernetes & Helm** | `Q5-kubernetes-helm/` | `workloads-running.png` | Deployments/Services/Ingress reconciled by the Helm chart in the live cluster |
| **Q6 — Observability** | `Q6-observability/` | `C4-golden-signals.png`, `C5-loki-logs.png`, `C6-loki-logs.png`, `C7-loki-logs.png` | Golden Signals dashboard, Loki JSON log streaming, `trace_id` derived fields |
| **Q7 — CI/CD & GitOps** | `Q7-cicd-gitops/` | `C2-argocd-app-detail.png`, `C3-argocd-self-heal.png`, `self-heal-scale-trigger.png`, `C9-argocd-reverted.png` | ArgoCD Synced/Healthy, drift self-healing after `--replicas=0`, revert reconciliation |
| **Q8 — Chaos & RCA** | `Q8-chaos-rca/` | `C8-alertmanager-firing.png`, `C8-grafana-5xx-spike.png`, `C9-grafana-recovery.png`, `C9-alerts-resolving.png`, `k6-chaos-run-results.txt` | GitOps-injected `CHAOS_ERROR_RATE=0.25` under 25-VU k6 load: alerts firing, 22% 5xx, recovery after revert (k6: 25.16% fault rate observed, p95 1.91 s, 1,436 orders) |

The chaos sequence in Q6–Q8 documents one continuous incident lifecycle: fault injected by GitOps commit → detected via Golden Signals → logs and alerts → GitOps revert → verified recovery.

---

## 5. Reproducing the Verification Suite

```bash
terraform -chdir=terraform validate
helm lint helm/shoplite
helm template shoplite helm/shoplite | grep -c "^kind:"
docker compose config --quiet
bash -n scripts/smoke-test.sh
cd ansible && for pb in playbooks/*.yml; do ansible-playbook -i inventory/hosts.yml "$pb" --syntax-check; done
cd .. && python -m pytest -q
make up && make smoke    # optional live gate
```

All commands are idempotent and safe to re-run at any time.

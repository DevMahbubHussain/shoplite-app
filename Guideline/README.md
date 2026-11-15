# ShopLite Developer Manual Testing Guideline

This directory contains the complete, interactive step-by-step manual testing and verification guide for the ShopLite Cloud-Native Platform.

---

## 🚀 Quick Start: Launching the Documentation UI

To launch the VitePress documentation website on your local machine:

```bash
# 1. Navigate into the Guideline directory
cd Guideline

# 2. Install dependencies (VitePress)
npm install

# 3. Start the local development server
npm run docs:dev
```

Once started, open your browser at:
👉 **[http://localhost:5173](http://localhost:5173)**

---

## 🛠 Available Scripts

From inside the `Guideline/` folder:

| Command | Action |
| :--- | :--- |
| `npm run docs:dev` | Starts the local interactive VitePress documentation server at `http://localhost:5173`. |
| `npm run docs:build` | Compiles the documentation into static production HTML in `docs/.vitepress/dist/`. |
| `npm run docs:preview` | Previews the compiled static HTML build locally. |

---

## 📄 Reading Without Running a Server (Terminal / Offline)

If you prefer to read the instructions directly from the terminal or in an editor without starting a Node server, refer to the standalone single-file markdown guide:

- **[MANUAL_TESTING_GUIDE.md](./MANUAL_TESTING_GUIDE.md)**

---

## 📋 What is Covered in this Guide?

The guideline covers manual terminal commands and pass criteria for all 8 core modules:

1. **Prerequisites & CLI Setup**: Python venv, dependencies, and environment files.
2. **Q1: API & Worker**: Running the 29 unit tests and manually testing all 7 endpoints with curl.
3. **Q2: Containerization & Smoke Test**: Multi-stage Docker builds (<150 MB, non-root UID 10001), Docker Compose, and `smoke-test.sh`.
4. **Q3: Linux Hardening**: Verifying user `deploy`, group `ops`, mode 750 with single ACL rule, `sshd -T`, systemd backup timers, and UFW firewall.
5. **Q4: AWS IaC & Ansible**: Validating Terraform VPC (2 AZs), ALB, ECR, remote S3 state, and Ansible playbooks.
6. **Q5: Helm & Kubernetes Workloads**: Linting Helm chart (`helm lint`), NetworkPolicy isolation, PDB, and HPA.
7. **Q6: Observability Stack**: Prometheus application metrics, Grafana Golden Signals dashboard, Loki structured logs, Tempo traces, and 5 alerts.
8. **Q7: CI/CD & ArgoCD Self-Healing**: GitHub Actions workflows and the live ArgoCD self-healing demonstration (`scale --replicas=0`).
9. **Q8: Chaos Engineering & RCA**: Running the 25 VU load test (`loadtest.js`), diagnosing issues via Grafana/Loki/Tempo, GitOps revert recovery, and the formal RCA report.
10. **Evidence & Screenshots Checklist**: Exact checklist of all 14 required terminal screenshots and deliverables for final assessment submission.

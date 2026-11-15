# ShopLite Learning & Interview Knowledge Base

This directory contains the interactive, bilingual (English & বাংলা) DevOps, SRE, and Cloud Architecture learning portal for the ShopLite Cloud-Native Platform.

---

## 🚀 Quick Start: Launching the Learning Portal UI

```bash
# 1. Navigate into the learning directory
cd learning

# 2. Install dependencies (VitePress)
npm install

# 3. Start the local development server (configured on port 5174)
npm run docs:dev
```

Open your browser at:
👉 **[http://localhost:5174](http://localhost:5174)**

*(Port 5174 is used to prevent conflict with the testing guideline on 5173).*

---

## 🛠 Available Scripts

From inside `learning/`:

| Command | Action |
| :--- | :--- |
| `npm run docs:dev` | Starts the local interactive VitePress learning server at `http://localhost:5174`. |
| `npm run docs:build` | Compiles the documentation into static production HTML in `docs/.vitepress/dist/`. |
| `npm run docs:preview` | Previews the compiled static HTML build locally. |

---

## 📚 Module Roadmap

1. **Phase 1: Local Foundations & Containerization**
   - 1.1 FastAPI Microservice Architecture & REST API Design
   - 1.2 Redis Reliable Queue Pattern & Worker Lifecycle
   - 1.3 Multi-Stage Docker Builds & Non-Root Container Security (<150 MB)
   - 1.4 Docker Compose Orchestration & Probe-Driven Smoke Testing
   - 1.5 Order Lifecycle State Machine & Edge Hardening
2. **Phase 2: Linux Administration & AWS Infrastructure as Code**
   - 2.1 Linux Server Administration & Hardening
   - 2.2 AWS Modular Infrastructure as Code (Terraform)
   - 2.3 Ansible Automated Node Bootstrapping & Cluster Provisioning
3. **Phase 3: Kubernetes Orchestration & GitOps**
   - 3.1 Kubernetes Unified Helm Chart & Workload Architecture
4. **Phase 3C: Enterprise CI/CD Pipelines**
   - 3C.1 GitHub Actions Test & Lint Automation
   - 3C.2 Trivy Container Vulnerability Scanning Gate
   - 3C.3 AWS OpenID Connect (OIDC) & Secure ECR Publishing
   - 3C.4 Automated GitOps Promotion Handshake
   - 3C.5 Enterprise CI/CD & GitOps Architecture Synthesis
5. **Phase 4: Observability & Chaos Engineering**
   - 4.1 Application Telemetry & Distributed Tracing
   - 4.2 Kubernetes Observability Workloads & Architecture
   - 4.3 Observability Infrastructure Helm Values Engineering
   - 4.4 Google SRE Golden Signals Dashboard Engineering
   - 4.5 Alertmanager Alert Rules & SRE Remediation Runbooks
   - 4.6 Chaos Engineering, Synthetic Load & Root Cause Analysis

---

## 🌐 Bilingual Design (দ্বিভাষিক শিখন পদ্ধতি)

Every topic includes:
- **Simple English Key Points**: Clear, bulleted architectural explanations.
- **বাংলা সারাংশ ও গুরুত্বপূর্ণ ধারণা**: Native conceptual summaries.
- **Interview Q&A (প্রশ্ন ও উত্তর)**: Real-world scenario-based DevOps & Cloud Architect interview questions and comprehensive model answers.

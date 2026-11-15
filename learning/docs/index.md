---
layout: home

hero:
  name: "ShopLite Learning Hub"
  text: "DevOps & Cloud Architecture Knowledge Portal"
  tagline: "Comprehensive, Key-Point Based Deep Dives & Real-World Interview QA with Bilingual English & বাংলা Summaries."
  actions:
    - theme: brand
      text: "Start with Phase 1 (App & Docker)"
      link: /phase-1-local-foundations-containerization/01-fastapi-microservices-architecture
    - theme: alt
      text: "Observability & Chaos"
      link: /phase-4-observability-chaos/01-application-telemetry

features:
  - title: "🧩 Phase 1: Microservices & Docker"
    details: "FastAPI asynchronous architecture, Redis reliable queue, worker lifecycle, non-root multi-stage Docker (<150 MB), and smoke testing."
  - title: "🛡️ Phase 2: Linux & Cloud IaC"
    details: "Enterprise SSH lockdown, POSIX ACLs, automated systemd backup timers, Terraform VPC (2 AZs), and Ansible bootstrapping."
  - title: "☸️ Phase 3 & 3C: Helm, CI/CD & GitOps"
    details: "Kubernetes unified Helm chart, Trivy CVE security scanning, AWS OIDC credential-less ECR publishing, and ArgoCD self-healing."
  - title: "📊 Phase 4: Observability & Chaos"
    details: "Prometheus metrics, Loki structured JSON logging, Tempo distributed tracing, Golden Signals dashboard, and formal RCA post-mortems."
---

## 🎯 Architecture Learning Roadmap & Module Breakdown

| Phase | Core Architectural Scope | Key Engineering Concepts | বাংলা মূল বিষয়বস্তু |
| :--- | :--- | :--- | :--- |
| **Phase 1** | **Application & Containerization** | FastAPI, asyncpg, Redis Queue, Worker loop, Docker multi-stage | ফাস্টএপিআই মাইক্রোসার্ভিস, রেডিস কিউ, ডকার মাল্টি-স্টেজ ও নন-রুট নিরাপত্তা |
| **Phase 2** | **OS Hardening & AWS IaC** | SSH CIS lockdown, POSIX ACLs (750 mode), systemd, Terraform, Ansible | লিনাক্স নিরাপত্তা, অটোমেটিক ব্যাকআপ টাইমার, টেরাফর্ম আইএসি এবং অ্যানসিবল |
| **Phase 3** | **Kubernetes & Workloads** | Helm packaging, NetworkPolicy, PDB, HPA, non-root securityContext | কিউবারনেটিস হেলম চার্ট, নেটওয়ার্ক পলিসি আইসোলেশন ও অটোস্কেলিং |
| **Phase 3C**| **Enterprise CI/CD Pipelines** | GitHub Actions, Trivy security gate, AWS OIDC, GitOps handshake | স্বয়ংক্রিয় সিআই/সিডি পাইপলাইন, ওআইডিসি অথেন্টিকেশন এবং ট্রাভি সিকিউরিটি |
| **Phase 4** | **Observability & Chaos** | OpenTelemetry, Prometheus, Loki, Tempo, Golden Signals, SRE Runbooks | ডিস্ট্রিবিউটেড ট্রেসিং, মেট্রিক্স, সেন্ট্রালাইজড লগিং ও ক্যাওস ইঞ্জিনিয়ারিং |

::: tip Bilingual Learning Philosophy (দ্বিভাষিক শিখন দর্শন)
Each module in this knowledge base provides:
1. **Key Points in Simple English**: Short, focused bullet points highlighting the *why* and *how*.
2. **বাংলা সারাংশ ও গুরুত্বপূর্ণ ধারণা**: Concise Bengali explanations designed to solidify conceptual clarity.
3. **DevOps & Cloud Architect Interview Q&A**: Real-world interview questions with detailed, scenario-tested model answers in English and Bengali.
:::

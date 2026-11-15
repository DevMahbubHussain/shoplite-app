import { defineConfig } from 'vitepress'

export default defineConfig({
  title: "ShopLite Learning & Interview Portal",
  description: "DevOps, SRE, and Cloud Architecture Knowledge Base with Bilingual (English & বাংলা) Key Points and Interview QA",
  themeConfig: {
    siteTitle: "ShopLite Learning Hub",
    nav: [
      { text: "Home", link: "/" },
      { text: "Phase 1: App & Docker", link: "/phase-1-local-foundations-containerization/01-fastapi-microservices-architecture" },
      { text: "Phase 2: Linux & AWS", link: "/phase-2-linux-hardening-aws-iac/01-linux-hardening" },
      { text: "Phase 3: K8s & CI/CD", link: "/phase-3-kubernetes-orchestration-gitops/01-helm-packaging" },
      { text: "Phase 4: Observability & Chaos", link: "/phase-4-observability-chaos/01-application-telemetry" }
    ],
    sidebar: [
      {
        text: "Phase 1: Application & Containerization",
        collapsed: false,
        items: [
          { text: "1.1 FastAPI Microservice Architecture", link: "/phase-1-local-foundations-containerization/01-fastapi-microservices-architecture" },
          { text: "1.2 Redis Reliable Queue & Worker", link: "/phase-1-local-foundations-containerization/02-redis-queue-worker-lifecycle" },
          { text: "1.3 Multi-Stage Docker & Security", link: "/phase-1-local-foundations-containerization/03-docker-multistage-nonroot-hardening" },
          { text: "1.4 Compose Orchestration & Smoke Test", link: "/phase-1-local-foundations-containerization/04-docker-compose-and-smoke-testing" },
          { text: "1.5 Order Lifecycle Edge Hardening", link: "/phase-1-local-foundations-containerization/05-edge-hardening-order-lifecycle" }
        ]
      },
      {
        text: "Phase 2: Linux Security & Cloud IaC",
        collapsed: false,
        items: [
          { text: "2.1 Linux OS Hardening & Access Control", link: "/phase-2-linux-hardening-aws-iac/01-linux-hardening" },
          { text: "2.2 AWS Terraform Modular Infrastructure", link: "/phase-2-linux-hardening-aws-iac/02-terraform-aws-iac" },
          { text: "2.3 Ansible Automated Node Bootstrapping", link: "/phase-2-linux-hardening-aws-iac/03-ansible-cluster-bootstrap" }
        ]
      },
      {
        text: "Phase 3: Kubernetes & Helm",
        collapsed: false,
        items: [
          { text: "3.1 Unified Helm Chart & Workloads", link: "/phase-3-kubernetes-orchestration-gitops/01-helm-packaging" }
        ]
      },
      {
        text: "Phase 3C: Enterprise CI/CD Pipelines",
        collapsed: false,
        items: [
          { text: "3C.1 Test & Lint Automation", link: "/phase-3c-ci-cd-pipelines/01-github-actions-test-lint" },
          { text: "3C.2 Trivy Container Security Scan Gate", link: "/phase-3c-ci-cd-pipelines/02-trivy-security-cve-scanning" },
          { text: "3C.3 AWS OIDC & Secure ECR Publishing", link: "/phase-3c-ci-cd-pipelines/03-aws-oidc-ecr-publishing" },
          { text: "3C.4 Automated GitOps Promotion Handshake", link: "/phase-3c-ci-cd-pipelines/04-gitops-promotion-handshake" },
          { text: "3C.5 CI/CD Architecture Synthesis", link: "/phase-3c-ci-cd-pipelines/05-ci-cd-architecture-synthesis" }
        ]
      },
      {
        text: "Phase 4: Observability & Chaos Engineering",
        collapsed: false,
        items: [
          { text: "4.1 Application Telemetry & Tracing", link: "/phase-4-observability-chaos/01-application-telemetry" },
          { text: "4.2 Kubernetes Observability Workloads", link: "/phase-4-observability-chaos/02-k8s-observability-workloads" },
          { text: "4.3 Infrastructure Helm Values", link: "/phase-4-observability-chaos/03-observability-infra-helm-values" },
          { text: "4.4 Golden Signals Dashboard Engineering", link: "/phase-4-observability-chaos/04-golden-signals-dashboard" },
          { text: "4.5 Alertmanager Rules & SRE Runbooks", link: "/phase-4-observability-chaos/05-alert-rules-runbooks" },
          { text: "4.6 Chaos Engineering & RCA Post-Mortem", link: "/phase-4-observability-chaos/06-chaos-engineering-rca" }
        ]
      }
    ],
    search: {
      provider: 'local'
    },
    footer: {
      message: 'ShopLite Cloud-Native Engineering Knowledge Base — Bilingual (English & বাংলা)',
      copyright: 'Copyright © 2026 ShopLite Platform Engineering'
    }
  }
})

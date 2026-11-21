import { defineConfig } from 'vitepress'

export default defineConfig({
  title: "ShopLite Manual Testing Guide",
  description: "End-to-End CLI Verification & Testing Guide for ShopLite Cloud-Native Platform",
  head: [
    ['link', { rel: 'icon', href: '/favicon.ico' }]
  ],
  themeConfig: {
    siteTitle: "ShopLite QA & Verification",
    nav: [
      { text: "Home", link: "/" },
      { text: "Guide", link: "/01-prerequisites-and-local-env" },
      { text: "Live Deployment", link: "/deploy/" },
      { text: "Checkpoints", link: "/10-evidence-and-screenshot-checklist" },
      { text: "RCA Incident", link: "/09-chaos-engineering-and-rca" }
    ],
    sidebar: [
      {
        text: "Live Deployment Walkthrough",
        items: [
          { text: "Overview & Toolchain", link: "/deploy/" },
          { text: "Phase 1: Local Compose Stack", link: "/deploy/01-local-compose-stack" },
          { text: "Phase 2: Linux Hardening (WSL)", link: "/deploy/02-linux-hardening" },
          { text: "Phase 3: Terraform Plan (Read-Only)", link: "/deploy/03-terraform-plan" },
          { text: "Phase 4: Kind Kubernetes Cluster", link: "/deploy/04-kind-cluster" },
          { text: "Phase 5: Helm & Observability", link: "/deploy/05-helm-observability" },
          { text: "Phase 6: GitOps with ArgoCD", link: "/deploy/06-gitops-argocd" },
          { text: "Phase 7: Chaos Drill & Recovery", link: "/deploy/07-chaos-and-recovery" },
          { text: "Phase 8: Teardown & Cost", link: "/deploy/08-teardown-and-cost" }
        ]
      },
      {
        text: "Getting Started",
        items: [
          { text: "Prerequisites & CLI Setup", link: "/01-prerequisites-and-local-env" },
          { text: "Architecture & Low-Level Design", link: "/02-architecture-and-catalog-api" },
        ]
      },
      {
        text: "Core Modules Verification",
        items: [
          { text: "Q1 & Q2: Docker & Smoke Testing", link: "/03-docker-and-smoke-testing" },
          { text: "Q3: Linux Hardening & Backups", link: "/04-linux-hardening-and-backups" },
          { text: "Q4: Terraform IaC & Ansible", link: "/05-aws-terraform-and-ansible" },
          { text: "Q5: Kubernetes & Helm Workloads", link: "/06-kubernetes-helm-workloads" },
          { text: "Q6: Observability (Metrics, Logs, Traces)", link: "/07-observability-stack" },
          { text: "Q7: CI/CD & ArgoCD Self-Healing", link: "/08-cicd-and-gitops-self-healing" },
          { text: "Q8: Chaos Engineering & RCA", link: "/09-chaos-engineering-and-rca" }
        ]
      },
      {
        text: "Submission & Evidence",
        items: [
          { text: "Required Screenshots & Artifacts Checklist", link: "/10-evidence-and-screenshot-checklist" }
        ]
      }
    ],
    search: {
      provider: 'local'
    },
    footer: {
      message: 'ShopLite Cloud-Native Platform Manual Testing & Verification Protocol',
      copyright: 'Copyright © 2026 ShopLite Platform Engineering'
    }
  }
})

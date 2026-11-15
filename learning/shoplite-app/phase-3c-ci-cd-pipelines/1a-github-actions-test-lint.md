# Phase 1A: GitHub Actions Workflow Architecture, Test Automation & Helm Linting — Deep Dive & Staff SRE Knowledge Base

> **Module:** ShopLite Cloud-Native E-Commerce Platform  
> **Repository:** `shoplite-app`  
> **Phase:** 1A — GitHub Actions Workflow Architecture & Quality Gates (Question 7 / Milestone 3)  
> **Branch:** `feature/ci-pipeline-actions`  
> **Parent Branch:** `feature/ci-cd-pipelines`

---

## 1. What Was Implemented

In this sub-phase, we engineered the foundational Continuous Integration (CI) pipeline for ShopLite in `.github/workflows/ci.yaml`:

```text
shoplite-app/
└── .github/
    └── workflows/
        └── ci.yaml       # GitHub Actions workflow: triggers, Python test suites & Helm linting
```

### 1.1 Trigger Architecture
The workflow implements a dual trigger model with cost-effective path filtering:
1. **Push Triggers:** Triggered automatically on push to `main`, scoped strictly to paths:
   - `services/**`
   - `helm/**`
   - `.github/workflows/**`
   Changes to purely documentation files (`README.md`, `docs/`, `learning/`) do NOT trigger expensive compute runners.
2. **Pull Request Triggers:** Runs on all PRs targeting `main` to enforce quality gates before merge.
3. **Manual Trigger (`workflow_dispatch`):** Enables on-demand manual execution directly from the GitHub UI for smoke testing or emergency runs.

### 1.2 Quality Gate Jobs
- **`test-catalog-api`:** Runs Python 3.11 unit tests using SQLite in-memory engine and mocked Redis queues. Executes the full 29-test API suite in $< 10\text{ seconds}$.
- **`test-order-worker`:** Runs worker scenario unit tests verifying state transitions (`PENDING` $\to$ `COMPLETED`), queue recovery sweeps, and SIGTERM graceful shutdown.
- **`lint-helm-chart`:** Installs Helm v3.14, executes `helm lint helm/shoplite`, and dry-run renders Kubernetes templates against both `values-dev.yaml` and `values-prod.yaml` to prevent malformed YAML reaching GitOps.

---

## 2. Why This Is Critical (AWS Well-Architected Framework Alignment)

### A. Operational Excellence (OPS04, OPS05)
- **Fast Feedback Loops:** CI pipelines must fail fast. Splitting API testing, Worker testing, and Helm linting into parallel jobs ensures developers receive feedback in $< 2\text{ minutes}$, keeping deployment velocity high.
- **Path-Filtered Compute Conservation:** Blindly triggering CI runs on every commit (such as markdown edits or diagram updates) wastes GitHub Actions runner minutes and clogs CI queues. Scoping triggers to code paths enforces operational efficiency.

### B. Reliability Pillar (REL07)
- **Contract-First Verification Before Packaging:** A container image is never built or pushed to Amazon ECR unless all contract tests and Helm template linting pass 100%. Broken application code or invalid YAML templates are intercepted at the earliest stage.

---

## 3. Staff SRE / Cloud Architect Interview Questions & Model Answers

### Q1: Why should unit tests in CI use in-memory dependencies (like SQLite in-memory or mocked Redis) rather than spinning up live PostgreSQL/Redis containers via Docker-in-Docker?
**Answer:**
1. **Speed & Execution Time:** Spinning up live Docker containers (PostgreSQL, Redis) in GitHub Actions requires container image pulling, network bridge configuration, and database readiness polling, adding 1–2 minutes per run. In-memory databases execute in $< 5\text{ seconds}$, keeping CI execution fast and reducing developer wait times.
2. **Determinism & Flakiness:** Live database containers introduce flakiness due to port binding collisions, transient network delays, and lingering dirty database states. In-memory databases are created and destroyed cleanly per test function, providing 100% deterministic isolation.
3. **Tiered Testing Strategy:** In-memory unit tests run on every commit. Full live database and container interactions are reserved for End-to-End Smoke Tests (`scripts/smoke-test.sh`) run during staging integration or release validation.

### Q2: What is the purpose of running `helm template` dry-runs in CI alongside `helm lint`?
**Answer:**
`helm lint` checks YAML syntax, indentation, and mandatory `Chart.yaml` fields, but it does NOT validate complex conditional Go template logic (`{{ if ... }}`, `{{- range ... }}`).
- An invalid template variable or indentation error inside a conditional block might pass `helm lint` if that block is not evaluated.
- Running `helm template <release> <chart> -f values-dev.yaml` and `-f values-prod.yaml` forces Helm to render the entire Kubernetes manifest output against real environment values, proving that every resource can be hydrated into valid Kubernetes YAML before reaching ArgoCD.

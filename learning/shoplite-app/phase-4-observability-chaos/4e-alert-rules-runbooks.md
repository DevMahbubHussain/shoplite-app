# Phase 4E: Alertmanager Rules, Routing & Production Runbooks — Deep Dive & Staff SRE Knowledge Base

> **Module:** ShopLite Cloud-Native E-Commerce Platform  
> **Repository:** `shoplite-app`  
> **Phase:** 4E — Alertmanager Rules, Routing Architecture & Runbooks (Question 6 / Milestone 4)  
> **Branch:** `feature/observability-alert-rules-runbooks`  
> **Parent Branch:** `feature/observability-stack`

---

## 1. What Was Implemented

In this sub-phase, we engineered the alerting and operational response layer for ShopLite, comprising declarative Prometheus alerting rules, Alertmanager notification routing, and comprehensive runbooks:

```text
monitoring/
├── alert-rules/
│   ├── alerts.yaml              # PrometheusRule CRD with all 5 mandatory alert definitions
│   └── alertmanager-config.yaml # Alertmanager notification trees and grouping routes
└── runbooks/
    ├── high-error-rate.md       # Triage & remediation for HTTP 5xx spikes
    ├── high-latency.md          # Triage for p95 latency degradation (> 1s)
    ├── queue-backlog.md         # Triage for Redis queue saturation (> 50 msgs)
    ├── pod-crash-looping.md     # Diagnosis for CrashLoopBackOff & OOMKilled
    └── node-disk-filling.md     # Emergency mitigation for disk utilization (> 85%)
```

### 1.1 Mandatory Alert Rule Specifications

| Alert Name | Severity | Threshold Expression | Duration | Target Runbook |
| :--- | :---: | :--- | :---: | :--- |
| `HighErrorRate` | **Critical** | `5xx rate > 5%` of total requests | `5m` | `monitoring/runbooks/high-error-rate.md` |
| `HighLatency` | **Warning** | `p95 latency > 1.0s` | `5m` | `monitoring/runbooks/high-latency.md` |
| `QueueBacklog` | **Warning** | `order_queue_depth > 50` | `10m` | `monitoring/runbooks/queue-backlog.md` |
| `PodCrashLooping`| **Critical** | `restart rate > 2` restarts | `10m` | `monitoring/runbooks/pod-crash-looping.md` |
| `NodeDiskFilling`| **Warning** | Available disk `< 15%` ($> 85\%$ used) | `5m` | `monitoring/runbooks/node-disk-filling.md` |

---

## 2. Why This Is Critical (AWS Well-Architected Framework Alignment)

### A. Operational Excellence (OPS04, OPS08, OPS10)
- **Symptom-Based Alerting (Google SRE Principle):** Traditional monitoring alerted on low-level causes (e.g. CPU > 80%), creating intense alert fatigue because high CPU does not necessarily mean users are suffering. Modern SRE practices prioritize **symptom-based alerts** that reflect user-facing service degradation (high 5xx errors, high response latency, delayed order fulfillment). Cause-based alerts (e.g. node disk filling) are reserved for impending infrastructural failure before customers are impacted.
- **Mandatory Runbook Annotations (C13):** Every alert MUST include an explicit `runbook_url` pointing to actionable remediation documentation. During an on-call paging event at 2:00 AM, engineers should not waste time searching wikis or wondering how to diagnose an issue. The runbook provides immediate, step-by-step diagnostic queries and mitigation options.

### B. Reliability Pillar (REL07, REL11)
- **Alertmanager De-duplication & Grouping:** Without grouping (`group_by: [alertname, service]`), a single database outage affecting multiple microservice pods could generate hundreds of individual notifications, drowning engineers in pager noise. Alertmanager groups these into a single notification batch with `group_wait: 30s`.

---

## 3. Staff SRE / Cloud Architect Interview Questions & Model Answers

### Q1: What is the difference between a Warning and a Critical alert, and how should Alertmanager route them?
**Answer:**
- **Critical Severity:** Indicates active, severe customer impact (e.g. `HighErrorRate > 5%` or core services crash looping) or immediate loss of data integrity. Critical alerts MUST page the on-call engineer immediately (via PagerDuty, Opsgenie, or urgent SMS) regardless of the hour. Repeat interval is tight ($1\text{h}$) until acknowledged.
- **Warning Severity:** Indicates performance degradation (e.g. `p95 latency > 1s`) or impending capacity exhaustion (`QueueBacklog > 50`, `NodeDiskFilling > 85%`) where the system is still functioning but heading toward failure. Warnings are routed to asynchronous team channels (Slack, email, ticket queue) during business hours without waking on-call engineers. Repeat interval is wider ($4\text{h}$ to $12\text{h}$).

### Q2: Why is the `for:` clause necessary in Prometheus alerting rules?
**Answer:**
Prometheus evaluates alert expressions every `evaluationInterval` (e.g. $15\text{s}$). If an alert had no `for:` clause, a single transient spike lasting 2 seconds (such as a temporary network hiccup or garbage collection pause) would immediately transition the alert to `FIRING` and page the engineer.
- Adding `for: 5m` requires the threshold condition to evaluate as true continuously for 5 full minutes.
- While the condition is true during this window, the alert sits in the `PENDING` state.
- Only if the degradation persists for the entire duration does Prometheus transition the alert to `FIRING`, eliminating flappy alerts and transient false positives.

### Q3: How do you prevent plain-text webhook secrets from leaking into Git in Alertmanager configurations?
**Answer:**
Alertmanager configuration files should never contain plain-text webhook tokens, Slack API URLs, or SMTP passwords in Git. In Kubernetes:
1. The base Alertmanager configuration is stored in a Kubernetes `Secret` (`alertmanager-kube-prometheus-alertmanager`).
2. Git repositories store a template with environment variable placeholders or use GitOps secret operators like **External Secrets Operator (ESO)** or **Sealed Secrets** to synchronize credentials securely from AWS Secrets Manager or HashiCorp Vault.
3. Helm charts can inject secrets dynamically via `configSecret: <secret-name>` in `alertmanagerSpec`.

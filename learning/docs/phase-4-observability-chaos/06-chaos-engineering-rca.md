# Phase 4.6: Chaos Engineering, Synthetic Load & Root Cause Analysis

> **Module:** ShopLite Cloud-Native Platform  
> **Key Concepts:** Chaos Engineering, Fault Injection, Synthetic Load Testing (`k6`), Telemetry Evidence Chain, Root Cause Analysis (RCA), GitOps Revert Recovery  

---

## 1. Key Learning Points (Simple English)

- **The Purpose of Chaos Engineering:** Proactively inject failures in a controlled environment to verify that telemetry, alert rules, autoscaling, and recovery mechanisms operate as designed under load.
- **The 4 Injected Fault Scenarios:**
  - `CHAOS_LATENCY_MS=1500`: Latency spike on product catalog.
  - `CHAOS_ERROR_RATE=0.20`: 20% order creation failure.
  - `CHAOS_MEMORY_LEAK=true`: Memory accumulation leading to pod OOMKilled.
  - `CHAOS_SLOW_DB=true`: Database delay triggering Redis queue backlog.
- **The Observability Chain (Constraint C14):**
  - Never peek at Git commits or environment variables.
  - Follow the strict evidence chain: Alertmanager Alert $\to$ Golden Signals Dashboard $\to$ Loki JSON Logs $\to$ Tempo Distributed Trace.
- **Recovery via GitOps:** Recover strictly by reverting the Git commit in `shoplite-gitops` and letting ArgoCD restore the cluster state.
- **Formal RCA Post-Mortem (`docs/RCA/RCA_REPORT.md`):** Documents MTTA (2m), MTTR (8m), UTC incident timeline, root cause, and preventative action items.

---

## 2. বাংলা সারাংশ ও মূল ধারণা (Bengali Summary)

- **ক্যাওস ইঞ্জিনিয়ারিং (Chaos Engineering):** সিস্টেমে ইচ্ছাকৃতভাবে সমস্যা বা ফেইলর (যেমন লেটেন্সি বাড়ানো বা মেমোরি লিক) তৈরি করে পরীক্ষা করা যে আমাদের অ্যালার্ট ও রিকভারি সিস্টেম বাস্তবে কাজ করে কিনা।
- **টেলিমেট্রি চেইন (Telemetry Chain):** সমস্যার কারণ খুঁজতে গিয়ে সরাসরি কোড বা এনভায়রনমেন্ট না দেখে শুধুমাত্র মনিটরিং টুলস দিয়ে ডায়াগনোসিস করা: প্রথমে অ্যালার্ট $\to$ তারপর গ্রাফানা ড্যাশবোর্ড $\to$ লোকি এরর লগ $\to$ টেম্পো ট্রেস।
- **গিটঅপ্স রিভার্ট (GitOps Revert):** লাইভ ক্লাস্টারে কোনো পরিবর্তন না করে শুধু গিটহাবে আগের ভালো কমিট রিভার্ট করলেই আর্গোসিডি স্বয়ংক্রিয়ভাবে পুরো ক্লাস্টারকে সুস্থ করে দেয়।
- **আরসিএ রিপোর্ট (Root Cause Analysis):** কোনো দুর্ঘটনা ঘটার পর কেন ঘটলো, কতক্ষণে ঠিক হলো এবং ভবিষ্যতে কীভাবে বন্ধ করা যায় তার পূর্ণাঙ্গ রিপোর্ট।

---

## 3. DevOps & Cloud Architect Interview Q&A

### Q1: What is the blameless post-mortem culture in Site Reliability Engineering (SRE)?
**Model Answer (English):**  
A blameless post-mortem assumes that engineers act with good intentions based on the information available to them at the time. Rather than finding a "human to blame", the investigation focuses on identifying systemic vulnerabilities: missing schema validation, inadequate canary testing, ambiguous runbooks, or brittle monitoring alerts. Blameless culture encourages engineers to report incidents transparently and implement preventative guardrails (e.g., CI configuration schema linters or automated canary rollback).

**বাংলা ব্যাখ্যা:**  
ব্লেমলেস পোস্ট-মর্টেম সংস্কৃতিতে কোনো মানুষের ওপর দোষ না চাপিয়ে সিস্টেম ও প্রক্রিয়ার দুর্বলতা খুঁজে বের করা হয়। কোনো মানুষ ভুল করতেই পারে, কিন্তু সিস্টেমের গার্ডরেইল বা সিআই গেট কেন সেই ভুল প্রোডাকশনে ঢুকতে দিলো—সেটাই ঠিক করা হয় যাতে ভবিষ্যতে একই ভুল দ্বিতীয়বার না ঘটে।

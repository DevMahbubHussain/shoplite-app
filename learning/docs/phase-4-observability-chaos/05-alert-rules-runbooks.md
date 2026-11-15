# Phase 4.5: Alertmanager Alert Rules & SRE Remediation Runbooks

> **Module:** ShopLite Cloud-Native Platform  
> **Key Concepts:** PrometheusRule CRDs, Alert Severities (`Critical`, `Warning`), Runbook URLs, Alert Fatigue Prevention, Notification Routing  

---

## 1. Key Learning Points (Simple English)

- **The 5 Required Production Alerts:**
  1. `HighErrorRate` (Severity: `Critical`): HTTP 5xx rate $> 5\%$ for 5m.
  2. `HighLatency` (Severity: `Warning`): p95 latency $> 1.0\text{s}$ for 5m.
  3. `QueueBacklog` (Severity: `Warning`): `order_queue_depth > 50` for 10m.
  4. `PodCrashLooping` (Severity: `Critical`): Container restarts increasing over 10m.
  5. `NodeDiskFilling` (Severity: `Warning`): Node disk usage $> 85\%$.
- **Actionable Alerts & Mandatory Runbooks:** Every alert must include a `runbook_url` pointing to an executable markdown runbook (`monitoring/runbooks/`). If an alert lacks an actionable remediation procedure, it causes alert fatigue and should not exist.
- **Alertmanager Routing:** Notifications route to on-call webhooks with deduplication (`group_by: [alertname]`), `group_wait: 30s`, and `repeat_interval: 4h`.

---

## 2. বাংলা সারাংশ ও মূল ধারণা (Bengali Summary)

- **অ্যালার্ট রুলস (Alert Rules):** প্রোডাকশন সিস্টেমে সমস্যা হওয়ার সাথে সাথে ইঞ্জিনিয়ারকে নোটিফিকেশন পাঠানোর ব্যবস্থা।
- **রানবুক (Runbooks):** অ্যালার্ট আসার পর ইঞ্জিনিয়ার কী করবেন—তার স্টেপ-বাই-স্টেপ সমাধান গাইড। শপলাইটের প্রতিটি অ্যালার্টের সাথে নির্দিষ্ট রানবুকের লিংক দেওয়া আছে।
- **অ্যালার্ট ফ্যাটিগ (Alert Fatigue):** অপ্রয়োজনীয় বা ফেক অ্যালার্ট বারবার আসলে ইঞ্জিনিয়াররা তা অগ্রাহ্য করা শুরু করে, ফলে আসল বিপদ মিস হয়ে যায়। তাই প্রতিটি অ্যালার্ট সুনির্দিষ্ট ও অ্যাকশনেবল হতে হবে।

---

## 3. DevOps & Cloud Architect Interview Q&A

### Q1: What is "Alert Fatigue", and how do SRE teams prevent it?
**Model Answer (English):**  
Alert fatigue occurs when on-call engineers are bombarded with non-actionable, noisy, or self-resolving alerts, leading to desensitization and missed real outages. SRE teams prevent it by:
1. **Symptom-Based Alerting:** Alert on customer-facing symptoms (errors $> 5\%$, high p95 latency) rather than internal causes (CPU spikes).
2. **For Durations:** Use `for: 5m` or `for: 10m` to prevent transient transient spikes from paging on-call staff.
3. **Actionable Runbooks:** Ensure every alert includes a linked runbook. If an alert requires no human action, it should be a ticket or dashboard metric, not a page.

**বাংলা ব্যাখ্যা:**  
ঘন ঘন অপ্রয়োজনীয় অ্যালার্ট বাজলে ইঞ্জিনিয়াররা বিরক্ত হয়ে পড়েন এবং আসল বড় কোনো সমস্যা হলেও তা এড়িয়ে যান। একে অ্যালার্ট ফ্যাটিগ বলে। এর প্রতিরোধে ৫ মিনিট স্থায়ী না হলে অ্যালার্ট না পাঠানো এবং প্রতিটি অ্যালার্টের জন্য স্পষ্ট রানবুক রাখা জরুরি।

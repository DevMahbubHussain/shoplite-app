# Phase 4.2: Kubernetes Observability Workloads & Architecture

> **Module:** ShopLite Cloud-Native Platform  
> **Key Concepts:** Prometheus Operator, ServiceMonitor CRDs, Grafana Loki, Promtail DaemonSet, Grafana Tempo, Derived Fields Linking  

---

## 1. Key Learning Points (Simple English)

- **Namespace Segregation:** All monitoring daemons reside in the dedicated `monitoring` namespace, strictly isolated from business workloads in `shoplite`.
- **Declarative Metric Scraping via ServiceMonitor:**
  - Instead of static Prometheus scrape configurations, Kubernetes uses the Prometheus Operator `ServiceMonitor` Custom Resource Definition (CRD).
  - Prometheus automatically discovers pods carrying labels `app.kubernetes.io/name: catalog-api` or `app.kubernetes.io/name: order-worker` and scrapes `/metrics` dynamically across pod restarts.
- **Unified Log-to-Trace Navigation:**
  - Containers stream single-line JSON logs to `stdout`.
  - Promtail scrapes node log files and forwards them to Loki.
  - In Grafana, Loki data source is configured with a **Derived Field** targeting regex `"trace_id":"([a-f0-9]{32})"`.
  - Clicking on a `trace_id` inside Loki instantly opens the correlated distributed trace in Tempo with zero manual copying.

---

## 2. বাংলা সারাংশ ও মূল ধারণা (Bengali Summary)

- **সার্ভিস মনিটর (`ServiceMonitor`):** কিউবারনেটিসে নতুন পট আসলে প্রমিথিউস কীভাবে বুঝবে কোথা থেকে মেট্রিক্স স্ক্র্যাপ করতে হবে? সার্ভিস মনিটর সিআরডি (CRD) লেবেল দেখে অটোমেটিকভাবে নতুন পটের মেট্রিক্স সংগ্রহ করে।
- **লগ থেকে সরাসরি ট্রেস লিঙ্কিং (Loki to Tempo):** লোকি (Loki) লগের ভেতর থেকে `trace_id` চিনে নেয়। গ্রাফানা ড্যাশবোর্ডে এরর লগে ক্লিক করলেই টেম্পো (Tempo)-তে গিয়ে দেখা যায় ঠিক কোন লাইনে বা ডাটাবেজ কুয়েরিতে সমস্যা হয়েছিল।

---

## 3. DevOps & Cloud Architect Interview Q&A

### Q1: How does a ServiceMonitor CRD decouple application developers from monitoring infrastructure?
**Model Answer (English):**  
In traditional Prometheus, monitoring engineers had to manually update a central `prometheus.yml` file and reload the server whenever a new application endpoint appeared. With the Prometheus Operator, developers define a `ServiceMonitor` manifest alongside their Helm chart, specifying matching labels and port names. Prometheus automatically queries the Kubernetes API, discovers target endpoints matching the selector, and dynamically updates its scraping pool without server downtime.

**বাংলা ব্যাখ্যা:**  
আগে নতুন এপিআই আসলে প্রমিথিউসের সেন্ট্রাল কনফিগ ফাইল এডিট করে সার্ভার রিলোড দিতে হতো। সার্ভিস মনিটর থাকায় অ্যাপ্লিকেশনের হেলম চার্টেই বলে দেওয়া যায় কোন পোর্টের মেট্রিক্স রিড করতে হবে, প্রমিথিউস স্বয়ংক্রিয়ভাবে তা খুঁজে নিয়ে স্ক্র্যাপ করা শুরু করে।

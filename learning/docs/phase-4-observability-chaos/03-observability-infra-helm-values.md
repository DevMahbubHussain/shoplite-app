# Phase 4.3: Observability Infrastructure Helm Values Engineering

> **Module:** ShopLite Cloud-Native Platform  
> **Key Concepts:** `kube-prometheus-stack`, Grafana Loki & Alloy, Tempo Storage, Retention Policies, OTLP Ingestion  

---

## 1. Key Learning Points (Simple English)

- **Infrastructure as Code for Monitoring:** Monitoring components are packaged and managed declaratively via Helm values in `monitoring/`:
  - `kube-prometheus-stack-values.yaml`: Configures Prometheus server, retention (15d), Alertmanager, and OpenMetrics exemplar support.
  - `loki-values.yaml`: Configures single-binary Loki with filesystem storage, JSON structured parsing, and Derived Fields linking to Tempo.
  - `tempo-values.yaml`: Configures OTLP gRPC (`4317`) and HTTP (`4318`) receivers with local block retention.
  - `promtail-values.yaml`: Configures Promtail daemonset to scrape `/var/log/pods` and drop extraneous noisy labels.

---

## 2. বাংলা সারাংশ ও মূল ধারণা (Bengali Summary)

- **হেলম দিয়ে মনিটরিং স্ট্যাক সেটআপ:** সব মনিটরিং কনফিগারেশন হেলম ভ্যালুজ ফাইলের মাধ্যমে কোড হিসেবে রাখা হয়েছে।
- **ওটিএলপি রিসিভার (Tempo OTLP):** টেম্পো ৪৩১৭ পোর্টে ডিস্ট্রিবিউটেড ট্রেস গ্রহণ করে।
- **রিটেনশন পলিসি (Retention):** ডিস্ক যাতে ভরে না যায় সেজন্য মেট্রিক্স ১৫ দিন এবং লগ নির্দিষ্ট সময় পর স্বয়ংক্রিয়ভাবে মুছে যাওয়ার জন্য রিটেনশন পলিসি সেট করা হয়েছে।

---

## 3. DevOps & Cloud Architect Interview Q&A

### Q1: What are Prometheus Exemplars, and how do they bridge metrics and distributed traces?
**Model Answer (English):**  
An exemplar is a reference to data outside the Prometheus metric set attached to a specific sample. When an HTTP request duration metric is recorded in a histogram bucket, OpenMetrics format attaches an exemplar carrying the active OpenTelemetry `trace_id`. In Grafana, clicking on an outlier latency spike on a Prometheus histogram panel displays the exact `trace_id` exemplar, allowing the operator to jump directly into the trace flame graph representing that exact high-latency request.

**বাংলা ব্যাখ্যা:**  
এক্সেমপ্লার হলো প্রমিথিউসের একটি আধুনিক ফিচার। যখন কোনো রিকোয়েস্টে অনেক বেশি লেটেন্সি বা স্লো রেসপন্স দেখা যায়, প্রমিথিউস মেট্রিক্সের সাথে ওই নির্দিষ্ট রিকোয়েস্টের `trace_id` জুড়ে দেয়। ফলে গ্রাফানায় লেটেন্সি স্পাইকে ক্লিক করলেই ওই নির্দিষ্ট স্লো রিকোয়েস্টের ট্রেস ওপেন হয়ে যায়।

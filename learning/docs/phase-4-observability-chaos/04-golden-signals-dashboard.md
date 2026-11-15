# Phase 4.4: Google SRE Golden Signals Dashboard Engineering

> **Module:** ShopLite Cloud-Native Platform  
> **Key Concepts:** Google SRE Golden Signals (Latency, Traffic, Errors, Saturation), Grafana as Code (`monitoring/dashboards/golden-signals.json`), PromQL Metrics Aggregations  

---

## 1. Key Learning Points (Simple English)

- **The Four Golden Signals of Monitoring (Google SRE):**
  1. **Latency:** The time it takes to service a request (p50, p95, p99 percentiles).
     - PromQL: `histogram_quantile(0.95, sum(rate(http_request_duration_seconds_bucket[5m])) by (le, route))`
  2. **Traffic:** A measure of demand on the system (Requests Per Second).
     - PromQL: `sum(rate(http_requests_total[1m])) by (route)`
  3. **Errors:** The rate of requests that fail (HTTP 5xx rate percentage).
     - PromQL: `(sum(rate(http_requests_total{status=~"5.."}[1m])) / sum(rate(http_requests_total[1m]))) * 100`
  4. **Saturation:** How "full" the service is (CPU, Memory, and Queue Backlog).
     - PromQL: Pod memory usage vs limit; gauge of `order_queue_depth`.
- **Business Throughput Signals:** Displays `orders_created_total` vs `orders_processed_total` and live ready worker replicas.

---

## 2. বাংলা সারাংশ ও মূল ধারণা (Bengali Summary)

- **গুগল এসআরই গোল্ডেন সিগন্যালস (Google SRE Golden Signals):** একটি সিস্টেম সুস্থ আছে কিনা তা বোঝার জন্য গুগল ৪টি প্রধান সিগন্যাল মনিটর করার পরামর্শ দেয়:
  1. **লেটেন্সি (Latency):** রিকোয়েস্ট প্রসেস করতে কত মিলি-সেকেন্ড সময় লাগছে (p95, p99)।
  2. **ট্রাফিক (Traffic):** প্রতি সেকেন্ডে কতগুলো রিকোয়েস্ট আসছে (RPS)।
  3. **এররস (Errors):** শতকরা কতভাগ রিকোয়েস্ট ৫xx ফেইল করছে।
  4. **স্যাচুরেশন (Saturation):** সিপিইউ, র‍্যাম এবং রেডিস কিউ কতটুকু ভর্তি হয়েছে।
- **ড্যাশবোর্ড অ্যাস কোড (Dashboard as Code):** পুরো ড্যাশবোর্ডটি মাউস দিয়ে ম্যানুয়ালি না বানিয়ে JSON কোড হিসেবে রাখা হয়েছে, যা কিউবারনেটিস কনফিগম্যাপ দিয়ে স্বয়ংক্রিয়ভাবে গ্রাফানায় লোড হয়ে যায়।

---

## 3. DevOps & Cloud Architect Interview Q&A

### Q1: Why should SREs monitor p95 and p99 latency percentiles instead of average (mean) latency?
**Model Answer (English):**  
Average latency is misleading and hides critical user dissatisfaction. If 90 requests take 10ms and 10 requests take 2,000ms, the average is ~209ms, which appears acceptable. However, 10% of users experienced an unacceptable 2-second delay. Percentiles measure the real distribution: p95 shows the latency threshold that 95% of users experienced, exposing the long-tail latency spikes that impact conversion rates and user retention.

**বাংলা ব্যাখ্যা:**  
গড় বা এভারেজ লেটেন্সি আসল সমস্যা লুকিয়ে রাখে। ৯৯ জন ইউজারের ১ মিলি-সেকেন্ড লাগলেও ১ জনের যদি ১০ সেকেন্ড সময় লাগে, এভারেজ দেখলে মনে হবে সিস্টেম ভালো আছে। কিন্তু p99 লেটেন্সি দেখলে ওই সবচেয়ে স্লো ইউজারের আসল ভোগান্তি প্রকাশ পায়।

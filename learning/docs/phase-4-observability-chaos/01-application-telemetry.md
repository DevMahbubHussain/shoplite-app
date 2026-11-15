# Phase 4.1: Application Telemetry & Distributed Tracing

> **Module:** ShopLite Cloud-Native Platform  
> **Key Concepts:** OpenTelemetry SDK, OTLP gRPC/HTTP Exporters, W3C TraceContext Propagation (`traceparent`), Prometheus Client Metrics, Context Extraction in Headless Workers  

---

## 1. Key Learning Points (Simple English)

- **The Three Pillars of Observability:**
  - **Metrics:** Aggregated numeric time-series data answering *what* is failing (e.g., error rate 20%).
  - **Logs:** Structured event records answering *why* it failed (e.g., specific stack trace).
  - **Traces:** Request journey through microservices answering *where* the bottleneck or failure occurred.
- **W3C TraceContext Propagation:**
  - `FastAPIInstrumentor` intercepts incoming HTTP requests and starts the root server span.
  - When `POST /orders` is invoked, `TraceContextTextMapPropagator().inject(carrier)` embeds the active `traceparent` (`00-<trace_id>-<span_id>-01`) into the Redis queue payload.
  - The asynchronous worker extracts the context via `TraceContextTextMapPropagator().extract(carrier)` and starts `worker_process_order` as a child span.
- **Zero Broken Traces:** Visualizing the trace in Grafana Tempo demonstrates the complete end-to-end journey:
  `HTTP POST /orders` $\to$ `redis.lpush` $\to$ `worker_process_order` $\to$ `postgres.execute(UPDATE orders)`.

---

## 2. বাংলা সারাংশ ও মূল ধারণা (Bengali Summary)

- **অবজারভেবিলিটির ৩টি স্তম্ভ (Metrics, Logs, Traces):**
  - **মেট্রিক্স:** সিস্টেমের সার্বিক অবস্থা সংখ্যায় দেখায় (যেমন: সিপিইউ কত %, এরর রেট কত %)।
  - **লগস:** বিস্তারিত টেক্সট বা ইভেন্ট ম্যাসেজ।
  - **ট্রেসেস:** একটি রিকোয়েস্ট কোন কোন সার্ভিসের মধ্য দিয়ে গেছে এবং কোথায় কত মিলি-সেকেন্ড সময় লেগেছে তার টাইমলাইন।
- **ডিস্ট্রিবিউটেড ট্রেসিং (OpenTelemetry & Tempo):** ব্যবহারকারী যখন ওয়েবসাইটে অর্ডারে ক্লিক করে, তখন একটি ইউনিক `trace_id` তৈরি হয়। এই আইডিটি রেডিস কিউ হয়ে ব্যাকগ্রাউন্ড ওয়ার্কারে যায়। ফলে আস্ত ট্রানজেকশনের সম্পূর্ণ ফ্লেমগ্রাফ গ্রাফানায় দেখা যায়।

---

## 3. DevOps & Cloud Architect Interview Q&A

### Q1: What is W3C TraceContext, and how does it prevent vendor lock-in?
**Model Answer (English):**  
W3C TraceContext is an open web standard defining universal HTTP and message headers (`traceparent` and `tracestate`) for distributed tracing. Prior to this standard, each vendor (Datadog, Dynatrace, AWS X-Ray, Zipkin) used proprietary headers (`X-B3-TraceId`, `x-amzn-trace-id`). By standardizing on W3C via the OpenTelemetry vendor-neutral SDK, ShopLite can swap backend trace storage (e.g. from Grafana Tempo to AWS X-Ray or Jaeger) by simply altering an OTLP endpoint configuration without touching application code.

**বাংলা ব্যাখ্যা:**  
আগে ভিন্ন ভিন্ন কোম্পানি (যেমন এডব্লিউএস, ডাটাডগ) তাদের নিজস্ব ফরম্যাটে ট্রেস আইডি পাঠাতো, যার ফলে এক ভেন্ডর থেকে অন্য ভেন্ডরে যাওয়া কঠিন ছিল। ডব্লিউথ্রিসি ট্রেসকন্টেক্সট একটি আন্তর্জাতিক ওপেন স্ট্যান্ডার্ড। ওপেনটেলিমেট্রি ব্যবহার করায় কোনো কোড পরিবর্তন ছাড়াই যেকোনো ট্রেসিং প্ল্যাটফর্মে ডাটা পাঠানো যায়।

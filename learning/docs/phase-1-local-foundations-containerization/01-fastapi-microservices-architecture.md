# Phase 1.1: FastAPI Microservice Architecture & REST API Design

> **Module:** ShopLite Cloud-Native Platform  
> **Component:** `services/catalog-api`  
> **Key Concepts:** FastAPI, Asynchronous I/O, SQLAlchemy 2.0 Async, Pydantic v2 DTOs, RESTful Design, Chaos Interceptors  

---

## 1. Key Learning Points (Simple English)

- **High-Throughput Asynchronous Framework:** FastAPI utilizes Python `asyncio` and `uvicorn` (ASGI server), achieving performance comparable to NodeJS and Go for I/O-bound e-commerce workloads.
- **Strict Separation of Concerns (OOP & SOLID):**
  - **Routers (`routers/`):** Handle HTTP transport, status codes, query parsing, and response serialization.
  - **Services (`services/`):** Encapsulate business logic, distributed trace context injection, and state transitions.
  - **Repositories (`repositories/`):** Isolate database persistence operations using SQLAlchemy AsyncSession.
- **Contract-First DTO Validation:** Pydantic v2 models (`ProductOut`, `OrderCreate`, `OrderOut`) validate request schemas and enforce immutable contracts, preventing untyped dictionary leakage.
- **Database Seeding on Startup:** On container startup, the application verifies the `products` table and automatically seeds $\ge 10$ e-commerce items if empty.
- **Chaos Injection Hooks:** Built-in middleware reads `CHAOS_LATENCY_MS` and `CHAOS_ERROR_RATE` to simulate real-world degraded dependencies without modifying application business logic.

---

## 2. বাংলা সারাংশ ও মূল ধারণা (Bengali Summary)

- **অ্যাসিঙ্ক্রোনাস মাইক্রোসার্ভিস (FastAPI & Asyncio):** ফাস্টএপিআই একটি অত্যন্ত দ্রুতগতির পাইথন ওয়েব ফ্রেমওয়ার্ক যা অ্যাসিঙ্ক আই/ও (I/O) সাপোর্ট করে। ফলে ডাটাবেজ কোয়েরি বা ক্যাশ অপারেশনের সময় সার্ভার থ্রেড ব্লক হয় না এবং একসাথে হাজার হাজার রিকোয়েস্ট হ্যান্ডেল করতে পারে।
- **লেয়ার্ড আর্কিটেকচার (Layered Architecture):** কোডকে মনোলিথিক বা জগাখিচুড়ি না বানিয়ে তিনটি প্রধান স্তরে ভাগ করা হয়েছে:
  1. **রাউটার (Routers):** শুধুমাত্র এইচটিটিপি রিকোয়েস্ট গ্রহণ ও রেসপন্স পাঠায়।
  2. **সার্ভিস (Services):** ব্যবসায়িক লজিক এবং ক্যাশ/কিউ কোঅর্ডিনেট করে।
  3. **রিপোজিটরি (Repositories):** সরাসরি পোস্টগ্রেস ডাটাবেজে কুয়েরি চালায়।
- **ডাটা ভ্যালিডেশন (Pydantic v2):** ভুল ডাটা টাইপ আসলে পাইড্যান্টিক স্বয়ংক্রিয়ভাবে `422 Unprocessable Entity` রিটার্ন করে, যা সার্ভারের ক্র্যাশ হওয়া প্রতিরোধ করে।

---

## 3. DevOps & Cloud Architect Interview Q&A

### Q1: Why choose FastAPI over traditional synchronous frameworks like Flask or Django for microservices?
**Model Answer (English):**  
FastAPI is built natively on ASGI (Asynchronous Server Gateway Interface) using `starlette` and `uvloop`. In an e-commerce microservices architecture where 90% of operations are I/O-bound (waiting on PostgreSQL, Redis, or external payment gateways), a synchronous framework (Flask/Django) allocates one OS thread per connection, causing thread starvation under high concurrency. FastAPI uses non-blocking coroutines (`async/await`), allowing a single process worker to handle thousands of concurrent requests with minimal memory footprint.

**বাংলা ব্যাখ্যা:**  
ফ্লাস্ক বা জাঙ্গো হলো সিঙ্ক্রোনাস—প্রতিটি রিকোয়েস্টের জন্য একটি করে থ্রেড আটকে থাকে। কিন্তু মাইক্রোসার্ভিসে বেশিরভাগ কাজই নেটওয়ার্ক আই/ও ভিত্তিক (ডাটাবেজ বা ক্যাশ কল)। ফাস্টএপিআই অ্যাসিঙ্ক্রোনাস হওয়ায় এক থ্রেডেই ইভেন্ট লুপের মাধ্যমে রিকোয়েস্ট প্রসেস করে, ফলে কম মেমোরিতেও বিপুল পরিমাণ ট্রাফিক হ্যান্ডেল করা যায়।

---

### Q2: How do you design reliable health probes (`/healthz` vs `/readyz`) in Kubernetes?
**Model Answer (English):**  
- `/healthz` (Liveness Probe): Must only verify if the web process is running and can process requests (`status: healthy`). It should **never** check external dependencies (DB/Redis). If it fails, Kubernetes kills and restarts the pod.
- `/readyz` (Readiness Probe): Verifies that dependencies (PostgreSQL pool and Redis connection) are actively reachable and ready to receive traffic. If PostgreSQL is temporarily down, `/readyz` returns `503 Service Unavailable`, prompting Kubernetes to remove the pod from service endpoints without unnecessarily restarting the container.

**বাংলা ব্যাখ্যা:**  
লাইভনেস প্রোব (`/healthz`) শুধু দেখে অ্যাপ প্রসেসটি জীবিত আছে কিনা। রেডিনেস প্রোব (`/readyz`) দেখে ডাটাবেজ ও ক্যাশ সক্রিয় কিনা। ডাটাবেজ সাময়িক ডাউন হলে রেডিনেস ফেইল করবে যাতে ট্রাফিক আসা বন্ধ হয়, কিন্তু পট ক্র্যাশলুপে পড়বে না।

---

### Q3: What is the architectural purpose of injecting W3C `traceparent` headers into asynchronous queues?
**Model Answer (English):**  
In distributed microservices, when an HTTP request (`POST /orders`) creates an asynchronous background job pushed to Redis, the direct HTTP network connection is broken. By generating an OpenTelemetry span, serializing its W3C `traceparent` header (`00-<trace_id>-<span_id>-01`), and embedding it in the Redis JSON payload, the headless background worker can extract the context and continue the exact same trace. This links the initial customer click, the queue delay, and the background database transaction into a single unified flame graph in Grafana Tempo.

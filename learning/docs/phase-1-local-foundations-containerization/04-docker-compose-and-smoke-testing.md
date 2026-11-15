# Phase 1.4: Docker Compose Orchestration & Probe-Driven Smoke Testing

> **Module:** ShopLite Cloud-Native Platform  
> **Components:** `docker-compose.yml`, `scripts/smoke-test.sh`, `Makefile`  
> **Key Concepts:** Container Dependencies (`condition: service_healthy`), Named Volumes, Synthetic Verification Probes, CI Fail-Fast Gates  

---

## 1. Key Learning Points (Simple English)

- **Deterministic Local Topology:** `docker-compose.yml` ties all 5 microservices (`web`, `catalog-api`, `order-worker`, `postgres`, `redis`) into a unified bridge network (`shoplite_net`).
- **Health Dependency Chains:**
  - `catalog-api` does not start until `postgres` and `redis` report `healthy` (`depends_on: { postgres: { condition: service_healthy } }`).
  - Eliminates startup race conditions where API containers crash in backoff loops waiting for PostgreSQL socket initialization.
- **Data Persistence:** PostgreSQL data is mounted to a named volume `postgres_data`, ensuring catalog seed data and orders survive container restarts.
- **Probe-Driven Smoke Testing (`scripts/smoke-test.sh`):**
  - Unit tests verify in-memory logic, but cannot prove that live network sockets, container networking, and real database drivers function together.
  - The automated smoke test executes 5 sequential probes against the live running stack:
    1. Probes `/readyz` with retries until both DB and Redis report healthy.
    2. Verifies frontend responds with HTTP 200.
    3. Verifies $\ge 10$ seeded products exist in the catalog.
    4. Places a live test order (`POST /orders`).
    5. Polls order status until the asynchronous worker updates it to `COMPLETED`.

---

## 2. বাংলা সারাংশ ও মূল ধারণা (Bengali Summary)

- **ডকার কম্পোজ অর্কেস্ট্রেশন (Docker Compose):** ৫টি কনটেইনারকে একসাথে রান ও কানেক্ট করার জন্য কম্পোজ ব্যবহার করা হয়।
- **হেলথ ডিপেনডেন্সি (`service_healthy`):** ডাটাবেজ পুরোপুরি রেডি হওয়ার আগে যদি ব্যাকএন্ড এপিআই চালু হয়, তবে ডাটাবেজ কানেকশন ফেইল করে অ্যাপ ক্র্যাশ করবে। কম্পোজে `condition: service_healthy` দিয়ে নিশ্চিত করা হয়েছে যে পোস্টগ্রেস ও রেডিস সুস্থভাবে চালু হওয়ার পরই এপিআই স্টার্ট হবে।
- **স্মোক টেস্টিং (Smoke Testing):** কোড লেখার পর পুরো সিস্টেম সত্যিকারের পরিবেশে কাজ করছে কিনা তা যাচাই করার জন্য ৫ ধাপের একটি অটোমেটিক টেস্ট স্ক্রিপ্ট (`smoke-test.sh`) চালানো হয়। এটি সরাসরি এপিআইতে অর্ডার পাঠায় এবং ওয়ার্কার ডাটাবেজে আপডেট করেছে কিনা তা নিশ্চিত করে।

---

## 3. DevOps & Cloud Architect Interview Q&A

### Q1: Why is `depends_on` without `condition: service_healthy` an anti-pattern in Docker Compose?
**Model Answer (English):**  
In Docker Compose, a basic `depends_on: [postgres]` declaration only waits for the *container process to start*, not for the *database service inside to become ready to accept TCP connections*. PostgreSQL takes several seconds to initialize database clusters and listen on port 5432. If an API starts immediately, its first connection pool request fails with `ConnectionRefusedError`. Using `condition: service_healthy` ensures Docker waits for PostgreSQL's internal `pg_isready` check to succeed before launching dependent applications.

**বাংলা ব্যাখ্যা:**  
শুধু `depends_on` দিলে ডকার কেবল দেখে কনটেইনারটি রান হয়েছে কিনা, কিন্তু ডাটাবেজ সার্ভার পুরোপুরি লোড হতে কয়েক সেকেন্ড সময় নেয়। এর ফলে এপিআই আগে চালু হয়ে ডাটাবেজ কানেকশন না পেয়ে ক্র্যাশ করে। `service_healthy` দিলে ডাটাবেজ রেডি হওয়া পর্যন্ত অপেক্ষা করে।

---

### Q2: How does a smoke test differ from unit and integration tests in a CI/CD pipeline?
**Model Answer (English):**  
- **Unit Tests:** Fast, isolated in-memory tests (mocking external DB/queues) verifying individual functions and classes.
- **Integration Tests:** Test interaction between multiple software components (e.g., repository interacting with an in-memory SQLite database).
- **Smoke Tests:** High-level, end-to-end "sanity checks" executed against a fully assembled, deployed environment. They verify that the complete infrastructure (networking, ingress, persistent volumes, environment configs, and background daemon loops) is alive and processing transactions from end to end before admitting production traffic.

**বাংলা ব্যাখ্যা:**  
ইউনিট টেস্ট কোডের ছোট ছোট ফাংশন মক করে পরীক্ষা করে। আর স্মোক টেস্ট হলো আসল বা প্রোডাকশন সদৃশ পরিবেশে সমস্ত কনটেইনার, নেটওয়ার্ক এবং ডাটাবেজ একসাথে ঠিকমতো কাজ করছে কিনা তার বাস্তবসম্মত পূর্ণাঙ্গ পরীক্ষা।

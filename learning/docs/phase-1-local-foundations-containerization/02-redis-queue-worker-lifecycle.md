# Phase 1.2: Redis Reliable Queue Pattern & Worker Lifecycle

> **Module:** ShopLite Cloud-Native Platform  
> **Component:** `services/order-worker` & Redis 7.2  
> **Key Concepts:** Reliable Queue Pattern, `BRPOPLPUSH` / `LREM`, Async Worker Loop, Graceful Termination (SIGTERM), Orphan Recovery Sweep  

---

## 1. Key Learning Points (Simple English)

- **The Problem with Standard Queues (`RPOP`):** If a worker pops an order using `RPOP` and immediately crashes (OOM, node termination, power outage), that message is lost forever because it was removed from Redis before being written to PostgreSQL.
- **Reliable Queue Pattern Solution:**
  1. `catalog-api` pushes order payloads to `orders:pending` via `LPUSH`.
  2. `order-worker` atomically pops from `orders:pending` and pushes to `orders:processing` using `BRPOPLPUSH` (or `BLMOVE`).
  3. The worker updates PostgreSQL (`status = 'PROCESSING'`), simulates business fulfillment (1–2s), and commits (`status = 'COMPLETED'`).
  4. Only upon successful database commit does the worker remove the payload from `orders:processing` via `LREM orders:processing 1 payload`.
- **Startup Recovery Sweep:** If the worker container was forcefully killed while processing, uncompleted orders remain trapped in `orders:processing`. On startup, the worker sweeps `orders:processing`, checks database state, and re-queues uncompleted items back to `orders:pending`.
- **Graceful Shutdown Protocol (`SIGTERM`):** On receiving `SIGTERM` from Kubernetes, the worker sets a shutdown event flag, stops picking up *new* messages, waits for the *current in-flight order* to finish writing to PostgreSQL, removes it from Redis, and exits cleanly.

---

## 2. বাংলা সারাংশ ও মূল ধারণা (Bengali Summary)

- **রিলায়্যাবল কিউ প্যাটার্ন (Reliable Queue):** সাধারণ কিউতে মেসেজ তোলার সাথে সাথে তা মুছে যায় (`RPOP`)। যদি প্রসেস করার আগেই ওয়ার্কার ক্র্যাশ করে, তবে অর্ডারের ডাটা চিরতরে হারিয়ে যাবে। এর সমাধানে `BRPOPLPUSH` ব্যবহার করা হয়, যা মেসেজটি `orders:pending` থেকে নিয়ে সাময়িকভাবে `orders:processing`-এ জমা রাখে।
- **ডাটাবেজ কমিট ও ডিলিট:** ওয়ার্কার সম্পূর্ণ ডাটাবেজ আপডেট (`status = 'COMPLETED'`) শেষ করার পরই কেবল `LREM` কমান্ড দিয়ে মেসেজটি মুছে ফেলে।
- **স্টার্টআপ রিকভারি সুইপ:** ওয়ার্কার চালু হওয়ার সময় যদি `orders:processing`-এ কোনো আটকে থাকা মেসেজ পায়, তবে সে ডাটাবেজ চেক করে স্বয়ংক্রিয়ভাবে সেগুলোকে পুনরায় `orders:pending`-এ পাঠিয়ে দেয় যাতে কোনো অর্ডার ড্রপ না হয়।
- **গ্রেসফুল শাটডাউন (SIGTERM):** কিউবারনেটিস যখন কোনো পট ডিলিট বা রিস্টার্ট করে, তখন এটি `SIGTERM` সিগন্যাল পাঠায়। ওয়ার্কার সাথে সাথে বন্ধ না হয়ে চলমান অর্ডারটির ডাটাবেজ রাইট শেষ করে সুন্দরভাবে প্রসেস বন্ধ করে।

---

## 3. DevOps & Cloud Architect Interview Q&A

### Q1: What is the "at-least-once" delivery guarantee, and how does ShopLite implement it with Redis?
**Model Answer (English):**  
"At-least-once delivery" guarantees that no message is lost in transit, even if workers fail unexpectedly, though messages may occasionally be processed more than once if failure occurs between the DB commit and queue cleanup. ShopLite achieves this through the Redis Reliable Queue pattern: messages remain safely preserved in `orders:processing` until PostgreSQL commits the completed state. If a crash occurs before `LREM`, the startup recovery sweep recovers the order, and the database status check ensures idempotent updates.

**বাংলা ব্যাখ্যা:**  
"এট-লিস্ট-ওয়ান্স ডেলিভারি" নিশ্চিত করে যে সিস্টেম ক্র্যাশ করলেও কোনো অর্ডার হারিয়ে যাবে না। রিলায়্যাবল কিউতে মেসেজ প্রসেসিং কিউতে ব্যাকআপ হিসেবে থাকে। ডাটাবেজে সফলভাবে সংরক্ষণ হওয়ার পরই কেবল কিউ থেকে মোছা হয়।

---

### Q2: How does Kubernetes handle `terminationGracePeriodSeconds` during worker deployments?
**Model Answer (English):**  
When Kubernetes drains a node or updates a Deployment, it sends a `SIGTERM` signal to container processes and initiates a countdown specified by `terminationGracePeriodSeconds` (default: 30s).
1. During this grace period, the application can finish ongoing transactions, close database connections, and flush telemetry traces.
2. If the process is still running after the countdown expires, Kubernetes sends `SIGKILL` (immediate forced termination).
3. In ShopLite, `terminationGracePeriodSeconds: 30` provides ample headroom for active 1–2 second order processing jobs to commit safely before pod shutdown.

**বাংলা ব্যাখ্যা:**  
কিউবারনেটিস একটি পট বন্ধ করার আগে `SIGTERM` পাঠিয়ে ৩০ সেকেন্ড অপেক্ষা করে (`terminationGracePeriodSeconds`)। এর মধ্যে ওয়ার্কার চলমান অর্ডারের কাজ শেষ করে প্রসেস বন্ধ করতে পারে। সময় শেষ হয়ে গেলে বাধ্য হয়ে `SIGKILL` দিয়ে বন্ধ করে দেওয়া হয়।

---

### Q3: When should you transition from Redis List queues to managed cloud brokers like Amazon SQS or Apache Kafka?
**Model Answer (English):**  
- **Redis Lists** are ideal for low-to-medium throughput, single-region clusters where simplicity, sub-millisecond in-memory latency, and minimal operational overhead are paramount.
- **Amazon SQS** is preferred when requiring fully managed serverless scaling, dead-letter queues (DLQ), built-in message deduplication (FIFO), and zero infrastructure maintenance.
- **Apache Kafka** is required when needing high-throughput distributed event streaming, long-term log retention, replayability for multiple consumer groups, and total partition ordering.

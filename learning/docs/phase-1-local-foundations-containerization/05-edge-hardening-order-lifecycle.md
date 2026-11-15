# Phase 1.5: Order Lifecycle State Machine & Edge Hardening

> **Module:** ShopLite Cloud-Native Platform  
> **Components:** `services/order-worker`, `services/catalog-api`  
> **Key Concepts:** State Machine (`PENDING → PROCESSING → COMPLETED | FAILED`), Typed Processing Outcomes, Retry with Exponential Backoff, Idempotent Terminal Writes  

---

## 1. Key Learning Points (Simple English)

- **Strict 4-State Order State Machine:**
  - `PENDING`: Order record inserted by API; message queued in `orders:pending`.
  - `PROCESSING`: Worker dequeues payload; stamps `PROCESSING` in PostgreSQL before starting delay.
  - `COMPLETED`: Fulfillment successful; updates PostgreSQL status to `COMPLETED` and sets `completed_at = NOW()`.
  - `FAILED`: Used when order enqueue fails or catastrophic unrecoverable business failure occurs.
- **Typed Processing Outcomes (`ProcessingResult` Enum):**
  - `SUCCESS`: Normal flow $\to$ removes payload via `LREM orders:processing 1 payload`.
  - `RETRY`: Transient errors (database connection loss, socket timeout) $\to$ `LPUSH` back to `orders:pending` with configurable backoff delay (`RETRY_DELAY_SECONDS`).
  - `DISCARD`: Permanent poison pill errors (corrupted JSON, missing `order_id`) $\to$ logs error and discards payload, avoiding infinite loop lockups.
- **Precision Financial Money Types:** `price` is modeled with SQL `NUMERIC(10,2)` instead of binary `Float` to prevent precision loss in billing and reporting.

---

## 2. বাংলা সারাংশ ও মূল ধারণা (Bengali Summary)

- **অর্ডারের ৪টি অবস্থা (State Machine):** প্রতিটি অর্ডার একটি সুনির্দিষ্ট জীবনচক্রের মধ্য দিয়ে যায়:
  1. `PENDING`: অর্ডার তৈরি হয়ে কিউতে জমা হওয়া।
  2. `PROCESSING`: ব্যাকগ্রাউন্ড ওয়ার্কার কাজ শুরু করার সাথে সাথে ডাটাবেজে স্ট্যাটাস আপডেট করা।
  3. `COMPLETED`: সফলভাবে কাজ সম্পন্ন হওয়া এবং সমাপ্তির সময় (`completed_at`) সংরক্ষণ।
  4. `FAILED`: কোনো কারণে ব্যর্থ হলে স্ট্যাটাস ফেইল্ড হিসেবে চিহ্নিত করা।
- **পয়জন মেসেজ হ্যান্ডলিং (Poison Messages):** যদি কোনো ভুল ফরম্যাটের মেসেজ কিউতে আসে যা কোড পার্স করতে পারে না, তবে সেটি বারবার রিট্রাই করলে সিপিইউ নষ্ট হবে (`Poison Message`)। তাই `ProcessingResult.DISCARD` দিয়ে ত্রুটিপূর্ণ মেসেজ সাথে সাথে বাদ দেওয়া হয় এবং সাকসেসফুল মেসেজ `LREM` দিয়ে ক্লিনআপ করা হয়।
- **টাকার হিসাবে `NUMERIC(10,2)`:** কম্পিউটারে সাধারণ ফ্লোটিং পয়েন্ট (`Float`) নাম্বারে সামান্য দশমিকের হেরফের হতে পারে (যেমন `0.1 + 0.2 = 0.30000000000000004`)। ফিন্যান্সিয়াল সিস্টেমে কখনোই ফ্লোট ব্যবহার করা যাবে না; তাই সঠিক হিসাবের জন্য `NUMERIC(10,2)` ব্যবহার করা হয়েছে।

---

## 3. DevOps & Cloud Architect Interview Q&A

### Q1: What is a "Poison Message" in distributed queuing, and how do you protect workers from it?
**Model Answer (English):**  
A poison message is a malformed or unprocessable payload that causes a consumer to crash or fail deterministically every time it attempts processing. Without safety bounds, the worker enters an infinite crash-loop (pop $\to$ crash $\to$ restart $\to$ pop again). Protection strategies include:
1. **Schema Validation:** Validate JSON payload upfront; if parsing fails, classify as permanent failure (`DISCARD`) and remove from queue immediately.
2. **Dead-Letter Queue (DLQ):** Track retry count (e.g., via Redis `INCR` or SQS receive count). If attempts $> 3$, eject to a dead-letter queue (`orders:dead`) for human inspection.
3. **Structured Alerting:** Trigger an alert whenever dead-letter queue depth $> 0$.

**বাংলা ব্যাখ্যা:**  
পয়জন মেসেজ হলো এমন একটি ত্রুটিপূর্ণ মেসেজ যা ওয়ার্কার প্রসেস করতে গেলেই ক্র্যাশ করে। ওয়ার্কার রিস্টার্ট হয়ে আবার একই মেসেজ তোলে এবং আবার ক্র্যাশ করে—এভাবে ক্র্যাশ-লুপ চলতে থাকে। এর সমাধান হলো: মেসেজের ফরম্যাট শুরুতে চেক করা, কয়েকবার রিট্রাইয়ের পর ফেইল হলে ডেড-লেটার কিউতে (`DLQ`) পাঠানো, যাতে বাকি অর্ডারগুলো আটকে না থাকে।

---

### Q2: Why is idempotency critical when consumer workers execute at-least-once delivery?
**Model Answer (English):**  
In at-least-once queuing, network blips or pod terminations between the database commit and the queue acknowledgement (`LREM`) cause the same message to be redelivered. If the consumer is not idempotent, it might charge a customer twice or fulfill an order duplicate times. By designing state transitions idempotently (e.g., `UPDATE orders SET status = 'COMPLETED' WHERE id = :id AND status != 'COMPLETED'`), receiving a duplicate delivery safely executes as a no-op without corrupting business data.

**বাংলা ব্যাখ্যা:**  
এট-লিস্ট-ওয়ান্স সিস্টেমে কোনো মেসেজ নেটওয়ার্ক ড্রপের কারণে দুইবার প্রসেস হতে পারে। যদি ওয়ার্কারের কোড ইডেমপোটেন্ট (Idempotent) না হয়, তবে একই অর্ডারের জন্য গ্রাহকের থেকে দুইবার টাকা কেটে নেওয়া হতে পারে। ইডেমপোটেন্ট ডিজাইনে একই মেসেজ একাধিকবার আসলেও ডাটাবেজে কোনো ভুল বা ডুপ্লিকেট পরিবর্তন হয় না।

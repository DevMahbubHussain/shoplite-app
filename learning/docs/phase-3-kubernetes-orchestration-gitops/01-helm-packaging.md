# Phase 3.1: Kubernetes Unified Helm Chart & Workload Architecture

> **Module:** ShopLite Cloud-Native Platform  
> **Key Concepts:** Single Unified Helm Chart (`helm/shoplite/`), StatefulSet with PVC, NetworkPolicy Isolation, PodDisruptionBudget (PDB), HorizontalPodAutoscaler (HPA), SecurityContext Constraints  

---

## 1. Key Learning Points (Simple English)

- **Single Unified Helm Chart (`helm/shoplite/`):** Manages the entire application topology under one chart with environment values (`values.yaml`, `values-dev.yaml`, `values-prod.yaml`).
- **PostgreSQL StatefulSet (`postgres-statefulset.yaml`):**
  - Uses `StatefulSet` with `volumeClaimTemplates` (5Gi PVC) rather than a Deployment to guarantee persistent, stable network identifiers and durable storage.
  - Features an initialization script to create tables and auto-seed $\ge 10$ products.
- **Cluster Network Isolation (`NetworkPolicy`):**
  - Blocks all direct external traffic to PostgreSQL (port 5432) and Redis (port 6379).
  - Only allows ingress traffic from pods with labels `app.kubernetes.io/name: catalog-api` or `app.kubernetes.io/name: order-worker`.
- **High Availability & Autoscaling:**
  - `PodDisruptionBudget` (`minAvailable: 1`) on `catalog-api` prevents voluntary evictions (node drains, cluster upgrades) from taking down the API.
  - `HorizontalPodAutoscaler` on `order-worker` scales replicas from 1 to 4 based on CPU utilization (target: 70%).
- **Pod Security Standards:** Every pod enforces non-root UID 10001, drops `ALL` Linux capabilities, and sets `readOnlyRootFilesystem: true`.

---

## 2. বাংলা সারাংশ ও মূল ধারণা (Bengali Summary)

- **হেলম চার্ট (Helm Chart):** কিউবারনেটিসের প্যাকেজ ম্যানেজার। আলাদা আলাদা ১০টা ইয়ামেল ফাইল রান না করে একটিমাত্র হেলম চার্টের মাধ্যমে পুরো সিস্টেম ইনস্টল বা আপগ্রেড করা যায়।
- **স্টেটফুলসেট (StatefulSet vs Deployment):** সাধারণ অ্যাপ্লিকেশনের জন্য ডিপ্লয়মেন্ট ব্যবহার করা হয়, কিন্তু ডাটাবেজের জন্য স্টেটফুলসেট ব্যবহার করা আবশ্যক। কারণ স্টেটফুলসেট ডাটাবেজের ভলিউম (PVC) ও নেটওয়ার্ক পরিচয় স্থায়ী রাখে, ফলে পট রিস্টার্ট হলেও ডাটা অক্ষত থাকে।
- **নেটওয়ার্ক পলিসি (NetworkPolicy):** ক্লাস্টারের ইন্টারনাল ফায়ারওয়াল। ওয়েব বা বাইরের কোনো পট সরাসরি ডাটাবেজ বা ক্যাশে ঢুকতে পারবে না; শুধুমাত্র ব্যাকএন্ড এপিআই এবং ওয়ার্কারই ডাটাবেজে কানেক্ট করতে পারবে।
- **অটোস্কেলিং ও পিডিবি (HPA & PDB):** ট্রাফিক বেড়ে গেলে ওয়ার্কার অটোমেটিক ১ থেকে ৪ টা পটে স্কেল হবে (HPA)। আর ক্লাস্টার মেইনটেন্যান্স বা নোড আপগ্রেডের সময় এপিআই যাতে ডাউন না হয়, সেজন্য অন্তত ১টি পট সবসময় চালু রাখার নিশ্চয়তা দেয় পিডিবি (`minAvailable: 1`)।

---

## 3. DevOps & Cloud Architect Interview Q&A

### Q1: Why should databases like PostgreSQL be deployed using a StatefulSet rather than a Deployment in Kubernetes?
**Model Answer (English):**  
A Kubernetes `Deployment` is designed for stateless workloads where pods are interchangeable, assigned random names, and share ephemeral storage. A `StatefulSet` provides three vital guarantees for stateful databases:
1. **Stable Network Identity:** Pods receive deterministic, persistent hostnames (`postgres-0`, `postgres-1`).
2. **Dedicated Storage per Replica:** Each pod is bonded to its own PersistentVolumeClaim that persists across rescheduling.
3. **Ordered Deployment and Termination:** Prevents race conditions during startup and ensures graceful shutdown before storage detachment.

**বাংলা ব্যাখ্যা:**  
ডিপ্লয়মেন্টে পটের নাম এলোমেলোভাবে তৈরি হয় এবং নতুন পট আসলে ডাটা হারিয়ে যেতে পারে। কিন্তু স্টেটফুলসেট প্রতিটি পটের নাম নির্দিষ্ট রাখে (`postgres-0`) এবং ডেডিকেটেড ডিস্ক ভলিউমের সাথে লক করে রাখে, যাতে পট রিস্টার্ট হলেও ডাটা ড্রপ না হয়।

---

### Q2: What is the security advantage of `readOnlyRootFilesystem: true` in production pods?
**Model Answer (English):**  
Enforcing `readOnlyRootFilesystem: true` prevents an attacker who exploits an application remote code execution (RCE) vulnerability from writing malicious binaries, modifying source scripts, tampering with configuration files, or downloading rootkits into the container. When temporary scratch space is needed (e.g. for `/tmp` or cache), an ephemeral in-memory `emptyDir` volume is explicitly mounted, containing disk writes to non-executable memory buffers.

**বাংলা ব্যাখ্যা:**  
রিড-অনলি রুট ফাইলসিস্টেম থাকলে কনটেইনারে কোনো ফাইল রাইট বা সেভ করা যায় না। ফলে কোনো হ্যাকার অ্যাপে ম্যালিশিয়াস স্ক্রিপ্ট বা ভাইরাস ডাউনলোড করে চালাতে পারে না। সাময়িক ডাটা রাখার জন্য শুধুমাত্র `/tmp` ফোল্ডারে মেমোরি মাউন্ট ব্যবহার করা হয়।

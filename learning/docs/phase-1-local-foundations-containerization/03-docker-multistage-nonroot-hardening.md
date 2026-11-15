# Phase 1.3: Multi-Stage Docker Builds & Non-Root Container Security

> **Module:** ShopLite Cloud-Native Platform  
> **Components:** `services/web`, `services/catalog-api`, `services/order-worker`  
> **Key Concepts:** Multi-Stage Builds, Alpine Minimal Base, Non-Root UID 10001, `.dockerignore`, Image Size Optimization (<150 MB), Inline HEALTHCHECK  

---

## 1. Key Learning Points (Simple English)

- **The Multi-Stage Build Advantage:**
  - **Stage 1 (Builder):** Installs heavy compilers (`gcc`, `musl-dev`, `libffi-dev`, `npm`), builds wheels or static assets, and strips debug symbols (`strip --strip-unneeded`).
  - **Stage 2 (Runner):** Uses a clean, stripped base image (`python:3.11-alpine` or `nginx:alpine`). Copies *only* the compiled virtual environment or static bundle. Zero compiler toolchains exist in the production image.
- **Strict Size Constraint (< 150 MB):** Eliminating compiler caches, test directories, `__pycache__`, and static assets keeps the final container images strictly under 150 MB (`web` ~38MB, `catalog-api` ~110MB, `order-worker` ~105MB). Small images ensure rapid pull times and fast cluster autoscaling.
- **Unprivileged Non-Root Security (UID 10001):**
  - Containers must never run as `root` (UID 0).
  - A dedicated unprivileged system account `appuser` (UID 10001, GID 10001) is created.
  - Files are owned by `appuser`, and the Dockerfile declares `USER 10001`.
  - Enables compatibility with strict Kubernetes security profiles (`runAsNonRoot: true`, `readOnlyRootFilesystem: true`, capabilities dropped: `["ALL"]`).
- **Inline Health Checks:** Every Dockerfile defines a native `HEALTHCHECK` command (`curl -f http://localhost:8000/healthz || exit 1`) enabling container engines to evaluate container health without relying on external orchestrators.

---

## 2. বাংলা সারাংশ ও মূল ধারণা (Bengali Summary)

- **মাল্টি-স্টেজ ডকার বিল্ড (Multi-Stage Build):** সাধারণত কোড কম্পাইল বা ডিপেনডেন্সি বিল্ড করার জন্য অনেক বড় বড় কম্পাইলার টুলস লাগে (`gcc`, `npm` ইত্যাদি)। মাল্টি-স্টেজ বিল্ডে দুটি ধাপ থাকে: প্রথম ধাপে বিল্ড করা হয়, আর দ্বিতীয় বা ফাইনাল ধাপে শুধু রেডি বাইনারিগুলো কপি করা হয়। এতে ইমেজের সাইজ নাটকীয়ভাবে ছোট হয়ে যায়।
- **১৫০ মেগাবাইটের নিচে ইমেজ সাইজ:** আমাদের সবগুলো সার্ভিসের সাইজ ১৫০ মেগাবাইটের অনেক নিচে। ছোট ইমেজ কিউবারনেটিস ক্লাস্টারে দ্রুত ডাউনলোড হয় এবং অটোস্কেলিংয়ের সময় দ্রুত পট চালু হতে সাহায্য করে।
- **নন-রুট ইউজার (Non-Root UID 10001):** ডিফল্টভাবে ডকার রুট (Root) ইউজার হিসেবে চলে, যা সিকিউরিটির জন্য বড় ঝুঁকি। কোনো হ্যাকার কনটেইনার হ্যাক করতে পারলে সে হোস্ট মেশিনের রুট অ্যাক্সেস পেতে পারে। তাই ডকারে `appuser` (UID 10001) তৈরি করে নন-রুট হিসেবে চালানো হয়েছে।

---

## 3. DevOps & Cloud Architect Interview Q&A

### Q1: Why is running containers as non-root (UID != 0) critical for Kubernetes production clusters?
**Model Answer (English):**  
In Linux, container isolation relies on namespaces and cgroups, but the Linux kernel is shared with the host machine. If a container runs as `root` (UID 0) and an attacker achieves a container breakout (via a kernel CVE, runc vulnerability, or misconfigured volume mount such as `/var/run/docker.sock`), the attacker immediately gains full root superuser privileges on the underlying host node. Declaring `USER 10001` and enforcing `runAsNonRoot: true` in the pod's `securityContext` confines the execution context, preventing privilege escalation.

**বাংলা ব্যাখ্যা:**  
ডকার কনটেইনার হোস্টের লিনাক্স কার্নেল শেয়ার করে। রুট (UID 0) হিসেবে অ্যাপ চালালে, অ্যাপে কোনো বাগ বা কার্নেল এক্সপ্লয়েট থাকলে অ্যাটাকার সম্পূর্ণ হোস্ট মেশিনের রুট পারমিশন পেয়ে যাবে। নন-রুট ইউজার (`UID 10001`) ব্যবহার করলে কনটেইনার থেকে বের হলেও হোস্টের কোনো ক্ষতি করতে পারবে না।

---

### Q2: What strategies did you apply in ShopLite to keep Python Docker images under 150 MB?
**Model Answer (English):**  
1. **Alpine Linux Base:** Switched from bloated Debian/Ubuntu base images (400MB+) to `python:3.11-alpine` (50MB base).
2. **Multi-Stage Build:** Installed compilers in Stage 1, compiled wheels, and copied `/opt/venv` to Stage 2.
3. **Binary Stripping:** Ran `strip --strip-unneeded *.so` on compiled C-extensions (`asyncpg`, `pydantic-core`), shaving 30MB of debug symbols.
4. **Pruning Artifacts:** Purged `pip`, `setuptools`, test directories, `.pyc` bytecodes, and `__pycache__`.
5. **Strict `.dockerignore`:** Excluded `.git`, `tests/`, local virtual environments, and `.env` files from entering the Docker build context.

**বাংলা ব্যাখ্যা:**  
১. আলপাইন লিনাক্স ব্যবহার করা হয়েছে।  
২. মাল্টি-স্টেজের মাধ্যমে কম্পাইলারগুলোকে ফাইনাল ইমেজ থেকে বাদ দেওয়া হয়েছে।  
৩. `strip` কমান্ড দিয়ে বাইনারি থেকে অপ্রয়োজনীয় ডিব্যাগ সিম্বল সরানো হয়েছে।  
৪. `.dockerignore` দিয়ে গিট ফোল্ডার ও টেস্ট ফাইল ডকার বিল্ডে ঢুকতে দেওয়া হয়নি।

---

### Q3: What is the difference between Docker `HEALTHCHECK` and Kubernetes `livenessProbe`?
**Model Answer (English):**  
- **Docker `HEALTHCHECK`:** Operates at the container engine runtime level (Docker daemon). It runs the specified command inside the container and changes container status from `starting` to `healthy` or `unhealthy` in `docker ps`. Docker itself does not automatically restart unhealthy containers unless orchestrated by Docker Compose or Swarm.
- **Kubernetes `livenessProbe`:** Operates at the cluster orchestration level (Kubelet). Kubelet periodically executes an HTTP request, TCP socket probe, or gRPC check from outside the container. If the probe fails beyond `failureThreshold`, Kubelet forcefully terminates and restarts the pod according to its `restartPolicy`.

# Phase 3C.4: Automated GitOps Promotion Handshake

> **Module:** ShopLite Cloud-Native Platform  
> **Key Concepts:** CI/CD vs GitOps Separation (The Golden Rule), Cross-Repository Handshake, Automated Image Tag Update, `shoplite-gitops`  

---

## 1. Key Learning Points (Simple English)

- **The Golden Rule of CI/CD vs GitOps Separation:**
  - **CI Pipeline (`shoplite-app`):** Builds images, runs unit tests, scans security vulnerabilities, publishes to Amazon ECR, and commits the updated image tag into `shoplite-gitops`.
  - **Absolute Prohibition:** The CI pipeline **NEVER** runs `kubectl apply` or `helm upgrade`.
  - **GitOps Engine (ArgoCD):** Observes `shoplite-gitops` repository and reconciles cluster state automatically.
- **The Cross-Repository Promotion Handshake:**
  1. Once container images are published to ECR, the workflow checks out the companion `shoplite-gitops` repository.
  2. Updates `envs/dev/values.yaml` image tags to the new short Git SHA (`catalogApi.image.tag = "${NEW_TAG}"`).
  3. Validates diff and commits: `deploy(dev): promote container images to ${NEW_TAG} [skip ci]`.
  4. ArgoCD detects the new Git commit, marks the application `OutOfSync`, and triggers an automated rolling update.

---

## 2. বাংলা সারাংশ ও মূল ধারণা (Bengali Summary)

- **সিআই/সিডি এবং গিটঅপ্স-এর গোল্ডেন রুল:** সিআই পাইপলাইনের কাজ হলো কোড টেস্ট করা, ইমেজ বিল্ড করা এবং ইসিআরে আপলোড করে গিটঅপ্স রেপোতে ইমেজের নতুন ভার্সন লিখে দেওয়া। সিআই পাইপলাইন কখনোই সরাসরি ক্লাস্টারে `kubectl` কমান্ড চালাবে না!
- **হ্যান্ডশেক প্রমোশন (Promotion Handshake):** ইমেজ পুশ হওয়ার পর সিআই স্বয়ংক্রিয়ভাবে `shoplite-gitops` রিপোজিটরির `values.yaml` ফাইলে নতুন ইমেজ ট্যাগ লিখে কমিট করে।
- **আর্গোসিডি অটোমেশন:** গিটঅপ্স রেপোতে নতুন কমিট আসা মাত্রই আর্গোসিডি পরিবর্তনটি শনাক্ত করে এবং ক্লাস্টারের পটগুলোকে নিরাপদে রোলিং আপডেট করে দেয়।

---

## 3. DevOps & Cloud Architect Interview Q&A

### Q1: Why is executing `kubectl apply` directly inside GitHub Actions considered a dangerous anti-pattern?
**Model Answer (English):**  
Directly executing `kubectl apply` from CI creates severe architectural, operational, and security flaws:
1. **Cluster Credential Exposure:** Requires injecting full cluster admin credentials (kubeconfig) into external CI runners, creating a catastrophic attack vector if CI is compromised.
2. **Configuration Drift:** Manual changes made on the cluster are silently overwritten without an audit trail, or CI deployments fail if cluster state diverged.
3. **Loss of Single Source of Truth:** Git no longer reflects the true running state of the cluster.
4. **No Native Rollback:** If a deployment fails midway, CI lacks self-healing reconciliation. GitOps with ArgoCD solves this by pulling state safely from within the cluster perimeter.

**বাংলা ব্যাখ্যা:**  
সিআই পাইপলাইনে `kubectl` চালালে পুরো ক্লাস্টারের অ্যাডমিন পাসওয়ার্ড গিটহাবে রাখতে হয়, যা বিশাল সিকিউরিটি রিস্ক। এছাড়া গিটহাব থেকে সরাসরি পুশ করলে ক্লাস্টারে কী চলছে তার গিট হিস্টোরি হারিয়ে যায়। গিটঅপ্স পদ্ধতিতে ক্লাস্টারের ভেতর থেকে আর্গোসিডি গিটহাব দেখে পরিবর্তন নিয়ে আসে—বাইরে থেকে কোনো কমান্ড চালাতে হয় না।

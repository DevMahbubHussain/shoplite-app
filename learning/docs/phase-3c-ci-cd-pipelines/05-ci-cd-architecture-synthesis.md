# Phase 3C.5: Enterprise CI/CD & GitOps Architecture Synthesis

> **Module:** ShopLite Cloud-Native Platform  
> **Key Concepts:** Complete Delivery Lifecycle, Dual-Repository Topology, Push vs Pull Models, Automated Drift Remediation, Compliance Alignment  

---

## 1. Key Learning Points (Simple English)

- **End-to-End Delivery Flow:**
  ```text
  Developer Commit ──> GitHub Actions CI (Lint, Test, Trivy) ──> Amazon ECR (OIDC)
                                                                        │
  Kubernetes Cluster <── ArgoCD Pull (Self-Heal) <── shoplite-gitops <──┘ (Promote Tag)
  ```
- **Push Model vs Pull Model:**
  - **Traditional CI Push:** CI runner reaches *into* the private cluster firewall to apply manifests. Requires open firewall ports and cluster admin keys stored externally.
  - **Modern GitOps Pull:** ArgoCD runs *inside* the private Kubernetes cluster, continuously polling Git over outbound HTTPS (443). Requires zero open inbound cluster ports.
- **Automated Self-Healing:** If an operator manually edits a pod, deletes a service, or scales replicas to 0 via `kubectl`, ArgoCD marks the cluster `OutOfSync` and automatically reverts the cluster to match the declared Git state within seconds.

---

## 2. বাংলা সারাংশ ও মূল ধারণা (Bengali Summary)

- **পুশ বনাম পুল মডেল (Push vs Pull Model):** সনাতন পদ্ধতিতে সিআই সার্ভার বাইরে থেকে ক্লাস্টারের ভেতর কমান্ড পুশ করতো। গিটঅপ্স পদ্ধতিতে ক্লাস্টারের ভেতরে থাকা আর্গোসিডি গিটহাব থেকে নতুন পরিবর্তন পুল করে আনে। এর ফলে ক্লাস্টারে বাইরে থেকে কোনো পোর্ট খুলতে হয় না।
- **সেলফ-হিলিং (Self-Healing):** ক্লাস্টারে কোনো দুর্ঘটনা ঘটলে বা কেউ ভুল করে কোনো পট ডিলিট করে দিলেও আর্গোসিডি স্বয়ংক্রিয়ভাবে গিটহাবে থাকা কনফিগারেশন দেখে ১৫ সেকেন্ডের মধ্যে সবকিছু আগের অবস্থায় ফিরিয়ে আনে।

---

## 3. DevOps & Cloud Architect Interview Q&A

### Q1: How does ArgoCD detect and remediate cluster drift?
**Model Answer (English):**  
ArgoCD maintains a continuous reconciliation loop:
1. It parses the target Helm chart or Kustomize manifests from Git at the declared revision (`targetRevision: main`).
2. It queries the live Kubernetes API server to inspect current cluster resources.
3. It performs a 3-way strategic merge diff.
4. If drift is detected (e.g., someone altered replicas with `kubectl scale`), ArgoCD marks the application `OutOfSync`.
5. With `selfHeal: true` enabled in the sync policy, ArgoCD immediately applies an automated reconciliation, issuing corrective Kubernetes API calls to restore the live cluster to match Git.

**বাংলা ব্যাখ্যা:**  
আর্গোসিডি সারাক্ষণ গিটহাবে থাকা কোড এবং ক্লাস্টারে বাস্তবে কী চলছে—এই দুটোর মধ্যে তুলনা করতে থাকে। যদি কোনো অমিল বা ড্রাফট পাওয়া যায়, সে সাথে সাথে ক্লাস্টারকে স্বয়ংক্রিয়ভাবে গিটহাবের ফাইলের মতো ঠিক করে দেয় (`selfHeal`)।

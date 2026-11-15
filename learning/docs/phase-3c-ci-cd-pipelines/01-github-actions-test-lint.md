# Phase 3C.1: GitHub Actions Test & Lint Automation

> **Module:** ShopLite Cloud-Native Platform  
> **Key Concepts:** GitHub Actions CI, Parallel Job Matrix, Pytest Automation, Helm Linting & Template Rendering, Fail-Fast Gates  

---

## 1. Key Learning Points (Simple English)

- **Shift-Left Quality Assurance:** Automated checks execute on every pull request and push to `main` before any container image build begins.
- **Parallelized Job Strategy:**
  - `test-catalog-api`: Runs pytest across API endpoints with coverage in an isolated runner.
  - `test-order-worker`: Validates asynchronous queue consumption, signal handling, and retry mechanics.
  - `lint-helm-chart`: Runs `helm lint helm/shoplite` and dry-run template rendering against both `values-dev.yaml` and `values-prod.yaml`.
- **Fast Feedback Loop:** By separating unit testing and Helm linting into independent matrix jobs, tests execute in under 45 seconds, providing immediate feedback to developers.

---

## 2. বাংলা সারাংশ ও মূল ধারণা (Bengali Summary)

- **শিফট-লেফট টেস্টিং (Shift-Left Testing):** কোড প্রোডাকশনে যাওয়ার অনেক আগেই গিটহাবে পুশ করার সাথে সাথে স্বয়ংক্রিয়ভাবে টেস্ট রান করা।
- **প্যারালাল জব ম্যাট্রিক্স (Parallel Jobs):** এপিআই টেস্ট, ওয়ার্কার টেস্ট এবং হেলম লিন্ট—এই ৩টি কাজ আলাদা আলাদা ভার্চুয়াল মেশিনে একসাথে প্যারালালে চলে, ফলে পুরো পাইপলাইনের সময় নাটকীয়ভাবে কমে যায়।
- **ড্রাই-রান টেমপ্লেট ভ্যালিডেশন:** ক্লাস্টারে ডিপ্লয় করার আগেই হেলম টেমপ্লেট রেন্ডার করে দেখা হয় কোনো সিনট্যাক্স বা ভ্যারিয়েবল জনিত ভুল আছে কিনা।

---

## 3. DevOps & Cloud Architect Interview Q&A

### Q1: Why should Helm linting and template rendering be integrated into CI pipelines?
**Model Answer (English):**  
Helm charts rely on Go templating, which can fail silently or produce invalid YAML if variables in `values.yaml` are mistyped or missing. Running `helm lint` catches chart metadata and formatting issues, while `helm template --dry-run` simulates manifest rendering against actual environment values. This guarantees that malformed YAML never breaks the GitOps reconciliation loop downstream in ArgoCD.

**বাংলা ব্যাখ্যা:**  
হেলম টেমপ্লেটে সামান্য স্পেস বা ভ্যারিয়েবলের বানানে ভুল থাকলেও কিউবারনেটিস ক্র্যাশ করতে পারে। সিআই পাইপলাইনে `helm lint` এবং `helm template` চালালে কোড মার্জ হওয়ার আগেই নিশ্চিত হওয়া যায় যে রেন্ডার হওয়া ইয়ামেল ফাইলটি ১০০% নির্ভুল।

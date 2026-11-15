# Phase 3C.3: AWS OpenID Connect (OIDC) & Secure ECR Publishing

> **Module:** ShopLite Cloud-Native Platform  
> **Key Concepts:** AWS OpenID Connect (OIDC), Short-Lived STS Credentials, Zero Long-Lived Static Keys, Amazon ECR Publishing, Short Git SHA Tagging  

---

## 1. Key Learning Points (Simple English)

- **Eliminating Static AWS Credentials:** Storing permanent AWS Access Keys (`AWS_ACCESS_KEY_ID` and `AWS_SECRET_ACCESS_KEY`) in GitHub Secrets is an enterprise security anti-pattern because leaked keys grant unbounded cloud access.
- **How AWS OIDC Authentication Works:**
  1. GitHub Actions runner requests an ephemeral JSON Web Token (JWT) signed by GitHub's OIDC provider.
  2. The workflow sends the JWT to AWS Security Token Service (STS) calling `sts:AssumeRoleWithWebIdentity`.
  3. AWS verifies the cryptographic signature against GitHub's public OIDC thumbprint.
  4. AWS validates trust policy claims (e.g., `repo:DevMahbubHussain/shoplite-app:ref:refs/heads/main`).
  5. If valid, AWS issues temporary, short-lived IAM credentials valid for 1 hour.
- **Deterministic Image Tagging:** Images are pushed with the short Git commit SHA (`git rev-parse --short HEAD`), full SHA, and `latest`, ensuring every deployment artifact is strictly traceable to the exact Git commit that produced it.

---

## 2. বাংলা সারাংশ ও মূল ধারণা (Bengali Summary)

- **জিরো স্ট্যাটিক পাসওয়ার্ড (Zero Static Keys):** গিটহাবে স্থায়ী অ্যামাজন পাসওয়ার্ড বা সিক্রেট কি সংরক্ষণ করা অত্যন্ত ঝুঁকিপূর্ণ। কোনো কারণে গিটহাব লিক হলে হ্যাকার ক্লাউডের পূর্ণ নিয়ন্ত্রণ নিতে পারে।
- **ওআইডিসি (OIDC - OpenID Connect):** এটি একটি আধুনিক টোকেন ভিত্তিক অথেনটিকেশন। গিটহাব রানার একটি সাময়িক সাইন করা টোকেন পাঠিয়ে অ্যামাজন এডব্লিউএস থেকে মাত্র ১ ঘণ্টার জন্য অস্থায়ী টোকেন গ্রহণ করে। কাজ শেষ হওয়া মাত্র এই কি অকার্যকর হয়ে যায়।
- **শর্ট গিট এসএইচএ (Short Git SHA):** ইমেজের ট্যাগ হিসেবে সবসময় গিট কমিট হ্যাশ (যেমন `b3f4d90`) ব্যবহার করা হয়, যাতে প্রোডাকশনে কোনো ইমেজ চললে এক ক্লিকেই বোঝা যায় এটি কোন কোড বা কমিট থেকে তৈরি হয়েছে।

---

## 3. DevOps & Cloud Architect Interview Q&A

### Q1: Explain the security benefits of AWS OIDC over static IAM user keys for CI/CD runners.
**Model Answer (English):**  
1. **Zero Credential Secrets to Rotate:** No static secret keys exist in GitHub, eliminating the risk of accidental commit leaks or secret exposure.
2. **Strict Cryptographic Scoping:** The AWS IAM trust policy explicitly validates the OIDC subject claim (`sub: "repo:org/repo:ref:refs/heads/main"`). Even if an unauthorized developer triggers an Action on an untrusted fork or branch, AWS STS rejects the exchange.
3. **Automated Ephemeral Expiration:** Credentials expire automatically within 1 hour, minimizing the window of opportunity for privilege abuse.

**বাংলা ব্যাখ্যা:**  
ওআইডিসিতে কোনো পাসওয়ার্ড গিটহাবে সেভ করতে হয় না। শুধু নির্দিষ্ট রিপোজিটরি এবং মেইন ব্রাঞ্চ থেকে আসা টোকেনই অ্যামাজন গ্রহণ করে। এছাড়া ১ ঘণ্টা পর স্বয়ংক্রিয়ভাবে কি মেয়াদোত্তীর্ণ হয়ে যায়, ফলে কি লিক হওয়ার কোনো সম্ভাবনাই থাকে না।

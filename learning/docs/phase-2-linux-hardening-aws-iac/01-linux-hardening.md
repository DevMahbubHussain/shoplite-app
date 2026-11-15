# Phase 2.1: Linux Server Administration & Hardening

> **Module:** ShopLite Cloud-Native Platform  
> **Key Concepts:** SSH Daemon Hardening (`PermitRootLogin no`, `PasswordAuthentication no`), Dedicated `deploy` User & `ops` Group, Mode 750 + Single POSIX ACL, Automated systemd Nightly Database Backup Timer, UFW Firewall  

---

## 1. Key Learning Points (Simple English)

- **CIS-Benchmark SSH Hardening:**
  - `PermitRootLogin no`: Completely disables remote `root` login, enforcing individual accountability.
  - `PasswordAuthentication no`: Disables passwords; authentication requires cryptographic SSH keys (`ed25519` or `rsa >= 4096-bit`).
  - `MaxAuthTries 3` & `LoginGraceTime 30`: Mitigates automated botnet brute-forcing and connection starvation.
- **Principle of Least Privilege (Users & Groups):**
  - Group `ops` and user `deploy` (`useradd -m -s /bin/bash -g ops deploy`).
  - Target directory `/var/log/shoplite/` owned by `root:ops` with octal permissions `750` (`rwxr-x---`).
  - Exactly **one** POSIX ACL rule applied: `setfacl -R -m g:ops:r-X /var/log/shoplite`.
  - **Rejection of Mode 777:** Mode 777 grants universal write/delete access, allowing unprivileged accounts or compromised services to modify or delete audit logs.
- **Systemd Automated Backup (`shoplite-backup.timer`):**
  - Runs nightly at `02:00:00 UTC` (`OnCalendar=*-*-* 02:00:00`).
  - Triggers `shoplite-backup.service` (Type: `oneshot`) executing `docker exec ... pg_dump | gzip`.
- **Network Perimeter Lockdown (UFW):**
  - Default: `deny incoming`, `allow outgoing`.
  - Inbound allowed ports: `22` (SSH), `80` (HTTP), `443` (HTTPS) only. All database and queue ports (5432, 6379) are dropped from the outside.

---

## 2. বাংলা সারাংশ ও মূল ধারণা (Bengali Summary)

- **রুট লগইন বন্ধ ও কী-ভিত্তিক অথেনটিকেশন:** ইন্টারনেটে ক্লাউড সার্ভার চালু করার সাথে সাথেই অটোমেটেড বটনেটগুলো পাসওয়ার্ড ব্রেক করার চেষ্টা করে। `PermitRootLogin no` এবং `PasswordAuthentication no` দিয়ে রুট ও পাসওয়ার্ড পুরোপুরি বন্ধ করে শুধুমাত্র এসএসএইচ কী (SSH Key) দিয়ে লগইন নিশ্চিত করা হয়েছে।
- **ইউজার আইসোলেশন ও পারমিশন ৭৫০:** সাধারণ অ্যাপ্লিকেশন বা অপারেটরদের জন্য `deploy` ইউজার এবং `ops` গ্রুপ তৈরি করা হয়েছে। লগ ফোল্ডারে `750` পারমিশন এবং একটিমাত্র এসিএল রুল (`setfacl`) দেওয়া হয়েছে।
- **কেন পারমিশন ৭৭৭ নিষিদ্ধ?** ৭৭৭ মানে যে কেউই ফাইলটি পড়তে, বদলাতে বা ডিলিট করতে পারবে। কোনো হ্যাকার সার্ভারে সামান্য এক্সেস পেলেই সব লগ মুছে দিয়ে প্রমান লোপাট করে ফেলতে পারবে।
- **সিস্টেমডি অটোমেটিক ব্যাকআপ:** প্রতিদিন রাত ২:০০ টায় (`UTC`) সিস্টেমডি টাইমার স্বয়ংক্রিয়ভাবে ডাটাবেজের ডাম্প (`pg_dump`) নিয়ে কম্প্রেস করে ব্যাকআপ ফোল্ডারে রেখে দেয়।
- **ফায়ারওয়াল সিকিউরিটি (UFW):** ডিফল্টভাবে সব ইনকামিং ট্রাফিক ব্লক করা হয়েছে। শুধু মাত্র ওয়েবসাইট ও এসএসএইচ-এর জন্য ২২, ৮০ ও ৪৪৩ পোর্ট খোলা রাখা হয়েছে।

---

## 3. DevOps & Cloud Architect Interview Q&A

### Q1: Why is `PermitRootLogin no` mandatory for SOC 2 and PCI-DSS compliance?
**Model Answer (English):**  
Shared administrative accounts like `root` destroy non-repudiation and access traceability. In any audit standard, every operational command must be attributable to a unique physical identity. When engineers log in using their personal named accounts with unique SSH keys and escalate privileges via `sudo`, every command is stamped with their username, IP, and timestamp in `/var/log/auth.log`, ensuring full auditability.

**বাংলা ব্যাখ্যা:**  
সরাসরি রুট ইউজার দিয়ে লগইন করলে কে কোন কমান্ড রান করেছে তা বের করা যায় না, কারণ লগ ফাইলে শুধুই `root` লেখা থাকে। তাই প্রতিটি ইঞ্জিনিয়ারের নিজস্ব ইউজার আইডি ও কী দিয়ে লগইন করে `sudo` দিয়ে কাজ করতে হয়, যাতে ভবিষ্যতে যেকোনো ঘটনার অডিট ও তদন্ত সম্ভব হয়।

---

### Q2: You update `/etc/ssh/sshd_config` on an EC2 instance, restart sshd, and get locked out. How do you recover?
**Model Answer (English):**  
1. **Prevention:** Always test configuration syntax before restarting (`sshd -t -f /etc/ssh/sshd_config`) and **never terminate your current active SSH session** until a secondary connection has succeeded in another terminal tab.
2. **Recovery in AWS:**
   - Connect immediately via **AWS Systems Manager (SSM) Session Manager** or **EC2 Serial Console**, which bypasses the network SSH daemon completely.
   - If SSM is unavailable, stop the EC2 instance, detach its EBS root volume, attach it to a temporary rescue EC2 instance, mount the volume, correct `/etc/ssh/sshd_config`, remount back to the original instance, and start it.

**বাংলা ব্যাখ্যা:**  
প্রতিরোধের নিয়ম হলো এসএসএইচ ফাইল পরিবর্তন করার পর কারেন্ট সেশন বন্ধ না করে আরেকটি নতুন টার্মিনালে টেস্ট লগইন করা। আর কোনো কারণে লকআউট হয়ে গেলে ক্লাউডে **AWS SSM Session Manager** বা সিরিয়াল কনসোল দিয়ে সরাসরি মেশিনে ঢুকে রিকভার করা যায়।

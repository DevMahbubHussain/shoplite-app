# Phase 2.2: AWS Modular Infrastructure as Code (Terraform)

> **Module:** ShopLite Cloud-Native Platform  
> **Key Concepts:** Terraform Modules (`network`, `compute`, `alb`, `ecr`), Remote S3 State Backend + DynamoDB Locking, Custom VPC Across 2 AZs, Zero Public SSH Access, AWS SSM Session Manager, AWS Budget Alarm ($20)  

---

## 1. Key Learning Points (Simple English)

- **Remote State Management:**
  - S3 bucket stores state with AES-256 / KMS server-side encryption and versioning.
  - DynamoDB table (`shoplite-tflocks`) manages distributed state locking with `LockID` key, preventing concurrent race conditions.
- **VPC Topology (2 Availability Zones):**
  - CIDR block: `10.0.0.0/16`.
  - 2 Public Subnets (`10.0.1.0/24`, `10.0.2.0/24`) host the Internet-facing ALB and NAT Gateway.
  - 2 Private Subnets (`10.0.10.0/24`, `10.0.20.0/24`) host Kubernetes Control Plane and Worker EC2 nodes.
- **Zero Public IP on Cluster Nodes:**
  - Control plane and worker instances possess zero direct public IPv4 addresses.
  - Outbound internet access for container image pulls and package updates routes through the NAT Gateway.
  - Administrative shell access operates via **AWS Systems Manager (SSM) Session Manager** with IAM role `AmazonSSMManagedInstanceCore`. Port 22 is completely closed to the Internet.
- **Cost Guarding:** An AWS Budget alarm at **$20 USD** sends automated email alerts, and all resources receive provider-level default tagging `project = "shoplite"`.

---

## 2. বাংলা সারাংশ ও মূল ধারণা (Bengali Summary)

- **মডুলার টেরাফর্ম (Modular Terraform):** কোড রিইউজেবল ও পরিষ্কার রাখতে ৪টি মডিউল তৈরি করা হয়েছে: `network` (ভিডিপিসি ও সাবনেট), `compute` (ইসি২ নোড), `alb` (লোড ব্যালেন্সার) এবং `ecr` (ইমেজ রেজিস্ট্রি)।
- **রিমোট স্টেট ও ডায়নামোডিবি লকিং (S3 & DynamoDB):** একাধিক ইঞ্জিনিয়ার যখন একসাথে কাজ করে, তখন লোকাল স্টেট ফাইল ব্যবহার করলে কনফ্লিক্ট বা ইনফাস্ট্রাকচার নষ্ট হওয়ার ঝুঁকি থাকে। তাই অ্যামাজন এস৩ বাকেটে রিমোট স্টেট রাখা হয়েছে এবং ডায়নামোডিবি দিয়ে `LockID` তৈরি করা হয়েছে যাতে দুজন একই সাথে `terraform apply` চালাতে না পারে।
- **প্রাইভেট সাবনেট ও নো পাবলিক আইপি:** কিউবারনেটিস ক্লাস্টারের সার্ভারগুলোর কোনো পাবলিক আইপি নেই! ফলে ইন্টারনেট থেকে কোনো হ্যাকার সরাসরি এগুলোকে স্ক্যান করতে পারে না। ইন্টারনেট থেকে ট্রাফিক শুধু লোড ব্যালেন্সার (ALB) হয়ে অ্যাপ্লিকেশনে ঢুকে।
- **জিরো এসএসএইচ পোর্ট (SSM Session Manager):** সার্ভারে ঢুকতে ২২ নম্বর পোর্ট খোলার কোনো প্রয়োজন নেই। অ্যামাজনের এসএসএম এজেন্ট ও আইএএম রোলের মাধ্যমে সরাসরি অ্যাডমিন এক্সেস নেওয়া হয়।

---

## 3. DevOps & Cloud Architect Interview Q&A

### Q1: Why should Kubernetes worker nodes always reside in private subnets behind a NAT Gateway rather than in public subnets?
**Model Answer (English):**  
Placing cluster nodes in private subnets adheres to defense-in-depth perimeter isolation:
1. **Zero Attack Surface:** Nodes lack public IPv4 addresses, preventing internet port scanning, unauthenticated kubelet access (port 10250), or SSH exploits.
2. **Controlled Ingress:** All incoming traffic is forced through the Application Load Balancer and Ingress Controller, which perform TLS termination, AWS WAF inspection, and path routing.
3. **Controlled Egress:** Outbound traffic flows via the NAT Gateway, providing a single elastic IP that can be whitelisted with external partners or security proxies.

**বাংলা ব্যাখ্যা:**  
পাবলিক সাবনেটে নোড রাখলে ইন্টারনেটের যেকোনো জায়গা থেকে সার্ভার অ্যাটাকের ঝুঁকি থাকে। প্রাইভেট সাবনেটে রাখলে সার্ভারের কোনো পাবলিক আইপি থাকে না, ফলে ইন্টারনেট থেকে সরাসরি কেউ আক্রমণ করতে পারে না। ট্রাফিক শুধুমাত্র লোড ব্যালেন্সার দিয়ে ফিল্টার হয়ে আসে।

---

### Q2: What happens if two engineers execute `terraform apply` simultaneously without state locking?
**Model Answer (English):**  
Without distributed locking (via DynamoDB's `LockID`), a catastrophic race condition occurs:
1. Both instances of Terraform read the existing `terraform.tfstate`.
2. Each process creates or updates cloud resources and attempts to overwrite the state file in S3.
3. The last writer wins, causing resources provisioned by the first process to be orphaned from state.
4. Subsequent runs fail with `ResourceAlreadyExists` or attempt to recreate resources, causing state corruption and production downtime. DynamoDB distributed locking halts the second command with `Error acquiring the state lock`.

**বাংলা ব্যাখ্যা:**  
ডায়নামোডিবি লকিং না থাকলে দুজন ইঞ্জিনিয়ার একসাথে কমান্ড চালালে স্টেট ফাইলে ওভাররাইট হয়ে যাবে। ফলে ক্লাউডে রিসোর্স তৈরি হলেও স্টেট ফাইল থেকে তার তথ্য মুছে যাবে (Orphaned Resource), যা ইনফাস্ট্রাকচার ভেঙে ফেলতে পারে।

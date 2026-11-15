# Phase 2B: AWS Infrastructure as Code (Terraform) — Deep Dive & Interview Guide

> **Module:** ShopLite Cloud-Native E-Commerce Platform  
> **Repository:** `shoplite-app`  
> **Phase:** 2B — AWS Infrastructure as Code with Terraform (Assessment Q4)  
> **Branch:** `feature/aws-vpc-infra`

---

## Sub-Phase 2B.1: Remote State Backend & Distributed Locking (`terraform/backend.tf`, `terraform/bootstrap/`)

### 1. What Was Implemented
We implemented an enterprise-grade, highly available, and encrypted Terraform remote state backend on live AWS infrastructure:
- **Live AWS S3 State Bucket:** `shoplite-tfstate-263303066497` in region `ap-southeast-1`:
  - **S3 Versioning Enabled:** Retains an immutable ledger of every historical `.tfstate` revision, allowing rollbacks if state becomes corrupted.
  - **Server-Side Encryption (SSE-S3 / AES256):** Encrypts all state files at rest.
  - **S3 Block Public Access:** Strict block on all public ACLs and bucket policies, ensuring zero public exposure of infrastructure state.
  - **Lifecycle Protection:** `prevent_destroy = true` protects against accidental destruction of the state backend.
- **Live AWS DynamoDB State Lock Table:** `shoplite-tflocks` in region `ap-southeast-1`:
  - **Partition Key:** `LockID` (String), conforming to HashiCorp's S3 backend locking protocol.
  - **Billing Mode:** `PAY_PER_REQUEST` (On-Demand), minimizing AWS infrastructure costs to zero when no applies are active.
  - **Point-in-Time Recovery (PITR):** Continuous backup of the lock database.
- **Backend Declaration:** Configured in `terraform/backend.tf` to point directly to the live S3 bucket and DynamoDB locking table with TLS encryption in transit (`encrypt = true`).

---

### 2. Why This Is Critical (AWS & Cloud-Native Production Alignment)

#### AWS Well-Architected Framework: **Security & Reliability (SEC01, SEC07, REL09)**
1. **Concurrency Control & Preventing Split-Brain Infrastructure:**
   - In production, multiple engineers or concurrent CI/CD pipeline runs (e.g. GitHub Actions executing PR plans and merges) may attempt to run `terraform apply` simultaneously.
   - Without distributed locking, two concurrent executions will read the same state, compute conflicting plans, and overwrite the remote state file simultaneously. This creates **split-brain resource destruction**, orphaned cloud resources, and catastrophic state file corruption.
   - DynamoDB implements an atomic distributed mutex: when an execution starts, Terraform writes an item with its unique execution UUID to `shoplite-tflocks` keyed by `LockID`. Any competing run immediately fails fast with a `StateLockError`.
2. **Confidentiality of Sensitive Infrastructure Secrets:**
   - Terraform state files (`.tfstate`) contain a complete JSON representation of all deployed resources, including raw outputs, database passwords, security group IDs, IAM role ARNs, and private subnet IP addresses.
   - Storing state locally or committing `.tfstate` to Git is a critical security vulnerability. An encrypted, access-controlled S3 bucket with strict IAM boundaries guarantees secrets are never exposed in source control.
3. **Disaster Recovery & State File Rollbacks:**
   - S3 Versioning ensures that if an apply is interrupted by network failure or an erroneous `terraform state rm`, previous state snapshots can be immediately restored from S3 version history.

---

### 3. Interview Questions & Comprehensive Model Answers

#### Q1 (Staff Cloud Architect): What happens under the hood when Terraform executes `terraform apply` with an S3 backend and DynamoDB locking?
**Model Answer:**  
1. **Lock Acquisition:** Terraform sends a `PutItem` request with a conditional expression (`attribute_not_exists(LockID)`) to the DynamoDB table `shoplite-tflocks`. The payload includes:
   - `LockID`: S3 bucket name + state path (e.g., `shoplite-tfstate-263303066497/infrastructure/terraform.tfstate-md5`).
   - `Info`: Execution ID, timestamp, operator username, and client hostname.
2. **State Retrieval:** Once the lock is acquired, Terraform issues an authenticated S3 `GetObject` to fetch the latest state JSON into memory and verifies its MD5 checksum.
3. **Plan / Execution:** Terraform performs the plan/apply, creating or modifying AWS resources via AWS APIs.
4. **State Flush:** Terraform writes the updated state JSON back to S3 via `PutObject` (creating a new S3 object version).
5. **Lock Release:** Terraform issues a `DeleteItem` request to DynamoDB to delete the `LockID` record, allowing subsequent executions to proceed.

#### Q2 (Production SRE Scenario): A GitHub Actions CI/CD runner is killed by an out-of-memory (OOM) killer or AWS Spot instance termination mid-apply. Subsequent Terraform runs fail with `Error: Error acquiring the state lock`. How do you safely resolve this?
**Model Answer:**  
- **Step 1: Verify No Active Execution:** Inspect CI/CD runners, terminal sessions, and AWS CloudTrail to verify that no active process is currently modifying infrastructure. Releasing a lock while an actual apply is running will corrupt state.
- **Step 2: Inspect Lock Metadata:** The error message displays the `Lock Info` containing the `Lock ID` GUID (e.g. `b4a2e8c1-1234-...`), the operator, and the start timestamp.
- **Step 3: Force Unlock:** Run the official HashiCorp CLI command:
  ```bash
  terraform force-unlock <LOCK_ID>
  ```
  This instructs Terraform to safely delete the orphaned entry from the DynamoDB table.
- **Alternative (Manual AWS Console/CLI):** If the CLI is blocked, query DynamoDB via `aws dynamodb get-item --table-name shoplite-tflocks --key '{"LockID":{"S":"<path>"}}'` and delete the item using `aws dynamodb delete-item`.

#### Q3 (Security & Compliance): Sensitive values like database passwords or private keys are stored in plaintext within `terraform.tfstate`. How do you achieve enterprise-grade security for the state file?
**Model Answer:**  
1. **Server-Side Encryption with Customer Managed Keys (AWS KMS CMK):** Encrypt the S3 state bucket with a dedicated KMS key (`aws_kms_key`). Only IAM principals with explicit `kms:Decrypt` and `kms:GenerateDataKey` permissions can read state objects.
2. **Strict S3 Bucket Policies & IAM Least Privilege:** Deny all access to the bucket except for the specific Terraform CI/CD IAM Execution Role. Block all public access via `aws_s3_bucket_public_access_block`.
3. **S3 Object Versioning & MFA Delete:** Enable versioning and require Multi-Factor Authentication (MFA) to delete state object versions.
4. **TLS 1.2+ In Transit:** Enforce `aws:SecureTransport` in the bucket policy (`"Effect": "Deny", "Condition": {"Bool": {"aws:SecureTransport": "false"}}`).
5. **Modern Architecture (Terraform Stacks / Ephemeral Secrets):** Use dynamic short-lived credentials (e.g. AWS Secrets Manager or HashiCorp Vault dynamic database secrets) so that credentials in `.tfstate` expire within minutes.


---

## Sub-Phase 2B.2 & 2B.3: Multi-AZ VPC Network Topology (`terraform/modules/network/`)

### 1. What Was Implemented
We designed and implemented a production-grade AWS VPC network topology adhering to strict defense-in-depth principles:
- **VPC Address Space:** `10.0.0.0/16` with full DNS hostnames and DNS resolution enabled.
- **Dual Availability Zone Resilience (`ap-southeast-1a`, `ap-southeast-1b`):**
  - **Public Subnets:** `10.0.1.0/24` (AZ1) and `10.0.2.0/24` (AZ2) with `map_public_ip_on_launch = true`. Dedicated exclusively to public Application Load Balancers and egress NAT Gateways. Annotated with `"kubernetes.io/role/elb" = "1"`.
  - **Private Subnets:** `10.0.10.0/24` (AZ1) and `10.0.20.0/24` (AZ2) with `map_public_ip_on_launch = false`. Dedicated to Kubernetes control plane and worker compute instances. Zero direct public internet accessibility. Annotated with `"kubernetes.io/role/internal-elb" = "1"`.
- **Egress Perimeter Isolation:**
  - **Internet Gateway (IGW):** Attached to the VPC for perimeter ingress/egress.
  - **Elastic IP & NAT Gateway:** Deployed in Public Subnet 1, routing private subnet traffic to the external internet (for container registry access and package updates) while preventing unsolicited inbound traffic.
  - **Route Table Segmentation:** Distinct public and private route tables isolating traffic boundaries.

---

### 2. Why This Is Critical (AWS & Cloud-Native Production Alignment)

#### AWS Well-Architected Framework: **Security & Reliability (SEC05, REL02)**
1. **Network Trust Boundaries (C2 Compliance):**
   - Direct public IP assignment on Kubernetes nodes is a critical vulnerability. If an unpatched CVE exists in the Linux kernel or Kubelet API, nodes with public IPs are directly exposed to scanning and exploitation.
   - Placing all compute workloads in private subnets with a NAT Gateway guarantees that instances can initiate outbound connections while remaining completely unreachable from the public internet.
2. **Multi-AZ High Availability:**
   - Deploying subnets across two distinct Availability Zones ensures that even if an entire AWS data center experiences a physical power failure or fiber cut, the surviving AZ continues serving traffic without interruption.
3. **Subnet Tags for Kubernetes Cloud Provider:**
   - Tagging public subnets with `kubernetes.io/role/elb = 1` and private subnets with `kubernetes.io/role/internal-elb = 1` enables the AWS Load Balancer Controller and Kubernetes Ingress Controller to automatically discover where to provision public vs internal load balancers.

---

### 3. Interview Questions & Comprehensive Model Answers

#### Q1 (Senior Network Architect): Why do we use separate Route Tables for Public and Private subnets instead of using a single route table?
**Model Answer:**  
In AWS VPC networking, a route table defines the next-hop target for all traffic exiting a subnet.  
- **Public Subnets** require a default route `0.0.0.0/0 -> igw-xxxx` (Internet Gateway) so that public ALBs have bidirectional connectivity with internet clients.
- **Private Subnets** require a default route `0.0.0.0/0 -> nat-xxxx` (NAT Gateway) so that instances can download updates without being assigned public IPv4 addresses.  
Because a subnet can only be associated with one route table, attempting to combine them into one table would either make private instances publicly reachable (if routed to IGW) or force public load balancers to route through a NAT gateway (breaking inbound public traffic).

#### Q2 (Cost Optimization vs High Availability): In our design, we deployed 1 NAT Gateway instead of 2. What are the trade-offs in an enterprise production architecture?
**Model Answer:**  
- **Cost Trade-off:** AWS charges approximately $32/month per NAT Gateway plus $0.045/GB of processed data. A single NAT Gateway saves ~$384/year and is optimal for development and staging environments.
- **Availability Trade-off:** A single NAT Gateway represents a single point of failure (SPOF) for private subnet egress. If `ap-southeast-1a` fails, private instances in `ap-southeast-1b` lose outbound internet connectivity.
- **Enterprise Recommendation:** For production Tier-1 systems, deploy **one NAT Gateway per Availability Zone** (multi-NAT architecture). Each private subnet routes to the NAT Gateway in its local AZ, eliminating cross-AZ data transfer charges and guaranteeing AZ fault isolation.

---

## Sub-Phase 2B.4 & 2B.5: Compute, Zero-Trust IAM & Perimeter ALB (`modules/compute/`, `modules/alb/`)

### 1. What Was Implemented
- **Control Plane & Worker Architecture:**
  - 1 Control Plane EC2 instance deployed in Private Subnet 1 (`10.0.10.0/24`).
  - 2 Worker EC2 instances distributed across Private Subnets (`10.0.10.0/24` and `10.0.20.0/24`).
  - Storage: Encrypted EBS `gp3` root volumes (30GB).
- **Zero-Port Administrative Access via AWS Systems Manager:**
  - IAM Instance Profile attached with `AmazonSSMManagedInstanceCore`.
  - Zero open SSH port 22 on Security Groups. Operators access nodes via `aws ssm start-session --target <instance-id>`.
- **Security Group Chaining:**
  - `ALB Security Group`: Ingress 80/443 from `0.0.0.0/0`. Egress strictly to Kubernetes NodePort range (`30000-32767`).
  - `Worker Security Group`: Ingress strictly from `alb-sg` on ports `30000-32767`. Intra-worker CNI overlay communication.
  - `Control Plane Security Group`: Ingress strictly from `worker-sg` on port `6443` (API Server) and intra-cluster `2379-2380` (etcd).
- **Application Load Balancer (ALB):**
  - Public ALB spanning across the two public subnets.
  - Target Group: Port `30080` (HTTP NodePort) forwarding to worker instances with health checks targeting `/healthz` on interval `15s`.

---

### 2. Why This Is Critical (AWS & Cloud-Native Production Alignment)

#### AWS Well-Architected Framework: **Security & Reliability (SEC01, SEC03, SEC05)**
1. **Security Group Chaining (Defense-in-Depth):**
   - Instead of allowing traffic by CIDR block, the worker security group explicitly references the ALB Security Group ID (`security_groups = [aws_security_group.alb.id]`). This ensures that only packets that have passed through the AWS ALB can reach node application ports, preventing port scanning from anywhere else in the VPC.
2. **SSM Session Manager vs Bastion Hosts:**
   - Eliminates the need for costly, publicly exposed Bastion/Jump hosts.
   - Eliminates SSH private key management, key rotation, and leaked `.pem` vulnerabilities.
   - Provides full session logging, auditing, and command recording shipped directly to AWS CloudWatch Logs and AWS CloudTrail.

---

### 3. Interview Questions & Comprehensive Model Answers

#### Q1 (Cloud Security Specialist): What is "Security Group Referencing" (Chaining), and why is it superior to CIDR-based rules?
**Model Answer:**  
Security Group Referencing involves specifying another Security Group ID (e.g. `sg-alb123`) as the `source` or `ingress` rule rather than an IP CIDR block (e.g. `10.0.1.0/24`).  
**Advantages:**
1. **Dynamic Scaling:** As nodes or load balancers scale out or receive new private IPs, traffic continues to be allowed automatically without updating IP rules.
2. **Zero Spoofing / Microsegmentation:** Even if an attacker gains control of an unauthorized EC2 instance within the same subnet, their packets are blocked because their instance does not belong to the authorized security group.

#### Q2 (Kubernetes Infrastructure): How does an external ALB route traffic to pods running inside a private Kubernetes cluster?
**Model Answer:**  
There are two production patterns:
1. **Instance Mode (NodePort Routing — used here):**
   - The ALB forwards public HTTP traffic to worker node IP addresses on a pre-assigned NodePort (e.g. `30080`).
   - The Linux kernel on the worker node uses `iptables` / `IPVS` / `kube-proxy` to forward packets across the cluster CNI overlay network to the actual pod IP, regardless of which node the pod resides on.
2. **IP Mode (AWS Load Balancer Controller + AWS VPC CNI):**
   - Pods are assigned native secondary IPv4 addresses directly from the VPC subnet via AWS ENIs.
   - The ALB routes packets directly to individual pod IPs, bypassing `kube-proxy` and NodePort routing for maximum performance and lower latency.

---

## Sub-Phase 2B.6 & 2B.7: Container Registry (ECR) & Cost Guard (`modules/ecr/`, `main.tf`)

### 1. What Was Implemented
- **3 Amazon ECR Repositories:**
  - `shoplite-web`, `shoplite-catalog-api`, `shoplite-order-worker`.
  - Configured with `scan_on_push = true` (automated Common Vulnerabilities and Exposures - CVE scanning).
  - Encrypted at rest via AES256.
- **ECR Lifecycle Retention Policies:**
  - Rule 1: Automatically purge untagged intermediate layer builds older than 14 days.
  - Rule 2: Retain only the last 10 tagged deployment releases, preventing unbounded storage growth.
- **AWS Budget Cost Alarm ($20 USD):**
  - Monitors actual and forecasted AWS spend against a strict $20 USD ceiling, sending SNS/email notifications when 80% and 100% thresholds are reached.

---

### 2. Interview Questions & Comprehensive Model Answers

#### Q1 (DevOps / SRE): Why is an ECR Lifecycle Policy essential in automated CI/CD pipelines?
**Model Answer:**  
In high-velocity CI/CD pipelines, every commit or pull request builds and pushes a new container image tagged with the Git SHA. Container images average 50MB to 500MB each. Over several months, thousands of images accumulate. AWS charges $0.10 per GB-month for ECR storage. Without lifecycle policies, orphaned images cost hundreds of dollars in unnecessary storage. An automated lifecycle policy purges intermediate layers and untagged artifacts while keeping only the latest stable release tags.

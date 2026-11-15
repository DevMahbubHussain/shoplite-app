# Phase 2A: Linux Server Administration & Hardening — Deep Dive & Interview Guide

> **Module:** ShopLite Cloud-Native E-Commerce Platform  
> **Repository:** `shoplite-app`  
> **Phase:** 2A — Linux Server Administration & Hardening (Assessment Q3)  
> **Branch:** `feature/linux-hardening`

---

## Sub-Phase 2A.1: SSH Daemon Hardening (`linux/sshd_config`)

### 1. What Was Implemented
We implemented an enterprise-grade, CIS-benchmark-aligned SSH daemon configuration file located at `linux/sshd_config`.

#### Key Directives Configured:
- `PermitRootLogin no`: Completely disables direct remote access as the `root` superuser.
- `PasswordAuthentication no`: Disables standard password challenges; authentication requires asymmetric cryptographic key pairs.
- `PubkeyAuthentication yes`: Enables cryptographic public-key authentication (`ssh-ed25519` or `ssh-rsa` $\ge 4096$-bit).
- `AuthorizedKeysFile .ssh/authorized_keys`: Enforces standard per-user public key storage with restrictive file permissions (`0600`).
- `ChallengeResponseAuthentication no`, `KerberosAuthentication no`, `GSSAPIAuthentication no`: Strips obsolete and non-utilized authentication mechanisms to minimize attack surface.
- `MaxAuthTries 3` & `LoginGraceTime 30`: Thwarts automated brute-force password/key guessing and SSH connection exhaustion.
- `ClientAliveInterval 300` & `ClientAliveCountMax 2`: Detects dead sessions and prunes orphaned pseudo-terminals (`pts`).
- `X11Forwarding no`: Prevents malicious X11 display hijacking or side-channel snooping.
- `Protocol 2`: Restricts SSH strictly to protocol version 2 (mitigating protocol downgrade attacks).

---

### 2. Why This Is Critical (AWS & Cloud-Native Production Alignment)

#### AWS Well-Architected Framework: **Security Pillar (SEC01, SEC02, SEC03)**
1. **Zero Public Attack Surface:**
   - In AWS, deploying an EC2 instance with `PermitRootLogin yes` or `PasswordAuthentication yes` exposed to an open Security Group (`0.0.0.0/0`) results in thousands of automated botnet brute-force attempts per hour within minutes of IP allocation.
   - Disabling passwords eliminates credential stuffing, dictionary attacks, and compromised password vulnerabilities.
2. **Identity & Access Management (Principle of Least Privilege):**
   - Direct `root` login destroys accountability. Every engineer must authenticate using their own non-root user identity (`deploy` or named user) via their provisioned public key.
   - When an administrator requires elevated privileges, they must execute `sudo`, generating an immutable audit trail in `/var/log/auth.log` or `/var/log/secure`.
3. **AWS Systems Manager (SSM) Integration:**
   - In modern AWS production VPCs, SSH port 22 is **never** exposed to the internet. Best practice is to close inbound port 22 entirely on Security Groups and manage instances via **AWS SSM Session Manager** (`aws ssm start-session`). 
   - However, for nodes in hybrid clouds, control plane maintenance, or emergency bastion architectures, when SSH is present, cryptographic hardening is mandatory to prevent lateral movement if an attacker breaches the perimeter.

---

### 3. Interview Questions & Comprehensive Model Answers

#### Q1 (Foundational): Why is `PermitRootLogin no` mandatory in cloud environments? What are the operational and compliance implications?
**Model Answer:**  
`PermitRootLogin no` enforces non-repudiation and access traceability. In any regulatory standard (SOC 2, PCI-DSS, ISO 27001, HIPAA), shared administrative credentials violate the core requirement for unique user identification. If an attacker gains root credentials or if multiple engineers share root access, individual attribution is lost—logs merely show `root` executed commands. By forcing login via individual unprivileged user accounts with SSH keys followed by audited `sudo` elevation, every action is tied to a specific key, timestamp, and IP, enabling full forensics.

#### Q2 (Scenario / Troubleshooting): You update `/etc/ssh/sshd_config` on an active production EC2 instance, restart the service, and find yourself locked out. What happened, how do you prevent this, and how do you recover?
**Model Answer:**  
- **Root Cause:** Common causes include syntax errors in the configuration, setting `PasswordAuthentication no` before the user's `~/.ssh/authorized_keys` is properly placed with `chmod 600` permissions and owned by the user, or firewall/SELinux blocking the SSH port.
- **Prevention:** 
  1. Always validate configuration syntax before restarting: `sshd -t -f /etc/ssh/sshd_config`.
  2. **Golden Rule of SSH Maintenance:** Never terminate your active SSH session. Open a secondary terminal tab and test logging in via `ssh -i key user@host`. If it fails, your primary session remains active to remediate the mistake.
- **Recovery in AWS:**
  1. Connect via **AWS Systems Manager (SSM) Session Manager** or **EC2 Serial Console**, which bypasses SSH daemon networking entirely.
  2. If SSM is unavailable, stop the EC2 instance, detach its root EBS volume, attach it to a recovery EC2 instance, mount the filesystem, fix `/etc/ssh/sshd_config` and file permissions, unmount, re-attach as root volume (`/dev/xvda` or `/dev/sda1`), and start the instance.

#### Q3 (Deep Architecture): How does W3C / modern zero-trust architecture replace traditional SSH key distribution in AWS?
**Model Answer:**  
Traditional SSH key management suffers from "key sprawl" where public keys become orphaned in `authorized_keys` when employees leave. Modern AWS architectures replace static keys using:
1. **AWS EC2 Instance Connect (EIC):** Generates ephemeral single-use SSH keys pushed via AWS API directly to instance RAM for 60 seconds, validated against IAM policies.
2. **AWS SSM Session Manager:** Relies on AWS IAM authentication and TLS-encrypted WebSockets via the SSM Agent, eliminating SSH keys, inbound open ports, public IPs, and bastion hosts altogether.
3. **HashiCorp Vault SSH Secrets Engine:** Issues short-lived signed SSH certificates valid for minutes rather than permanent keys.

---

## Sub-Phases 2A.2 & 2A.3: User Isolation, Group Management & POSIX ACLs (`linux/setup-users-permissions.sh`)

### 1. What Was Implemented
We authored an idempotent setup script `linux/setup-users-permissions.sh` establishing unprivileged operations identity and strict access controls on application logs.

#### Key Actions:
- Group creation: `groupadd -f ops` creates the operations group.
- Dedicated user: `useradd -m -s /bin/bash -g ops deploy` creates the deploy user with primary group `ops`.
- Base directory ownership & mode:
  - `chown -R root:ops /var/log/shoplite`
  - `chmod 750 /var/log/shoplite` (Read/Write/Execute for `root`, Read/Execute for `ops`, Zero access `---` for others/world).
- **Single POSIX ACL Rule:**
  - `setfacl -R -m g:ops:r-X /var/log/shoplite` (Recursively grants group `ops` read and execute/traverse rights on directories and read rights on files).
  - Explicit compliance: Contains exactly **one** `setfacl` rule without the default ACL variant (`-d`).

---

### 2. Why This Is Critical (AWS & Cloud-Native Production Alignment)

#### AWS Well-Architected Framework: **Operational Excellence & Security (OPS08, SEC04)**
1. **Rejection of Mode `777`:**
   - Directory mode `777` (`rwxrwxrwx`) allows any process or unprivileged system user (e.g. `nobody`, `www-data`, compromised container escapes) to read, append, truncate, or delete sensitive transaction logs containing order data or audit records.
   - Attackers could overwrite logs to conceal malicious activity or inject ANSI escape code exploits.
2. **Principle of Least Privilege via POSIX ACLs:**
   - Standard Unix permissions (`owner:group:other`) are binary and restrictive. If an application daemon writes logs as `root` (or a dedicated log forwarder), standard permissions cannot easily grant read-only access to monitoring agents without granting write rights or making the files world-readable.
   - POSIX ACLs provide granular access: group `ops` (used by operators or the AWS CloudWatch unified agent / Promtail) receives read and traversal access (`r-X`), preserving confidentiality without compromising log integrity.
3. **Log Shipping to AWS CloudWatch / Loki:**
   - In production, local logs in `/var/log/shoplite/` are scraped by agents like **AWS CloudWatch Agent**, **Promtail**, or **FluentBit** and shipped to S3/CloudWatch/Loki. Granting the agent's service account group membership in `ops` ensures seamless log forwarding without running the daemon as root.

---

### 3. Interview Questions & Comprehensive Model Answers

#### Q1 (Fundamental): Why is permission mode `777` strictly forbidden in production, especially for log directories?
**Model Answer:**  
Mode `777` gives read, write, and execute permissions to all users on the operating system. For a log directory:
1. **Integrity Loss:** Any compromised unprivileged process can wipe, modify, or truncate audit trails, destroying forensic evidence.
2. **Confidentiality Breach:** Sensitive transactional or operational data (IPs, customer IDs, trace IDs) becomes readable by any unauthorized local process.
3. **Execution Hijack:** If a directory has `777` permissions, an attacker can create symlinks, replace binary wrappers, or drop malicious scripts executed by automated cron/systemd jobs. Mode `750` ensures that only `root` can write or delete files, `ops` can inspect, and `others` have zero visibility.

#### Q2 (Deep Dive): What is the difference between standard POSIX permissions and POSIX ACLs (`setfacl`/`getfacl`)?
**Model Answer:**  
Standard POSIX permissions support only three permission sets: User (Owner), Group, and Other (UGO). If an application requires access for multiple distinct groups (e.g. `root` owns, `ops` reads, `audit` monitors, `backup` reads) without exposing files to `other`, standard permissions fail because a file has only one primary group.  
POSIX ACLs (Access Control Lists) extend this by allowing multiple named users (`u:username:rwx`) and multiple named groups (`g:groupname:r-x`) to have specific permissions attached to an inode, independently of the file's primary owner and group.

#### Q3 (Scenario): Why did the rubric specify `setfacl -R -m g:ops:r-X` with uppercase `X` rather than lowercase `x`?
**Model Answer:**  
In POSIX file permissions, lowercase `x` grants execution permissions to both directories and files. Uppercase `X` represents **conditional execution**:
- It grants execute/traversal permission (`x`) to **directories** (which is necessary for a user or agent to enter (`cd`) and list contents within the directory tree).
- It **does not** grant execute permission to regular files unless the file already has execute permission set for another user.  
This guarantees that log files remain strictly non-executable data files (`-rw-r-----`) rather than executable scripts, eliminating the risk of accidental execution or exploit staging.


---

## Sub-Phases 2A.4, 2A.5 & 2A.6: Automated Database Backup via systemd (`shoplite-backup.service`, `shoplite-backup.timer`, `shoplite-backup.sh`)

### 1. What Was Implemented
We implemented an enterprise-grade automated database backup architecture using native Linux systemd timers instead of legacy cron jobs:
- **`linux/systemd/shoplite-backup.service`:** A systemd unit configured with `Type=oneshot`, execution user `root`, service dependencies `After=docker.service Requires=docker.service`, and failure recovery semantics (`Restart=on-failure`, `RestartSec=30s`).
- **`linux/systemd/shoplite-backup.timer`:** A systemd timer triggered daily at `02:00:00 UTC` (`OnCalendar=*-*-* 02:00:00`) with `Persistent=true` (ensuring that if the node was powered off or rebooting at 02:00 UTC, the backup executes immediately upon boot).
- **`linux/systemd/shoplite-backup.sh`:** A fault-tolerant shell script that:
  - Invokes `pg_dump` non-interactively via `docker exec -t shoplite-postgres pg_dump -U shoplite_user -d shoplite_db`.
  - Streams the SQL stream through `gzip` on the fly to minimize I/O overhead and compress backup size by up to 80-90%.
  - Sets strict file permissions `0600` on the generated backup file and `0700` on `/var/backups/shoplite/`.
  - Implements automated retention rotation pruning archives older than 7 days (`find -mtime +7 -delete`).

---

### 2. Why This Is Critical (AWS & Cloud-Native Production Alignment)

#### AWS Well-Architected Framework: **Reliability & Operational Excellence (REL09, REL13, OPS07)**
1. **Systemd Timers vs Legacy Cron:**
   - **Observability:** Systemd timers integrate natively with `systemd-journald`. Every backup execution, return code, stdout, and stderr is centrally logged and searchable via `journalctl -u shoplite-backup.service`.
   - **Catch-up Capability (`Persistent=true`):** If an EC2 instance undergoes maintenance, automated patching via AWS Systems Manager Patch Manager, or an instance stop/start event during the scheduled window, standard cron skips the job. Systemd with `Persistent=true` records missed events in timestamp files (`/var/lib/systemd/timers/`) and fires immediately upon boot.
   - **Resource Management & Dependencies:** Systemd enforces explicit service ordering (`After=docker.service`). If the Docker engine or PostgreSQL container is not running, systemd delays or fails gracefully with structured telemetry rather than silently spawning zombie cron processes.
2. **Disaster Recovery (RPO & RTO Alignment):**
   - In cloud architectures, nightly logical backups (`pg_dump`) complement EBS snapshots and continuous WAL archiving (e.g. AWS Aurora continuous backups).
   - A compressed, portable `.sql.gz` dump allows immediate restoration across heterogeneous environments (e.g. local Docker development, staging Kubernetes cluster, or disaster recovery in a secondary AWS region).
3. **AWS S3 Cloud Offloading:**
   - In a production AWS deployment, this script would pipe the compressed stream directly to an Amazon S3 Glacier or Standard bucket:
     `aws s3 cp "${BACKUP_FILE}" s3://shoplite-database-backups-production/` with S3 Object Lock (WORM compliance) and Lifecycle policies.

---

### 3. Interview Questions & Comprehensive Model Answers

#### Q1 (Architecture / Comparison): Why are systemd timers preferred over traditional cron in modern cloud infrastructure?
**Model Answer:**  
Systemd timers provide significant operational advantages:
1. **Unified Logging:** Timers trigger services whose output is captured in `systemd-journald` with rich metadata (unit name, exit code, execution duration), eliminating the need for brittle cron mailers (`sendmail`) or custom log redirection hacks (`>> /var/log/backup.log 2>&1`).
2. **Dependency & Order Management:** Timers can declare `Requires=`, `After=`, and `Wants=`, guaranteeing prerequisites like network, storage mounts (EBS/EFS), or the Docker daemon are healthy before execution starts.
3. **Missed Event Recovery:** The `Persistent=true` directive ensures jobs missed during instance shutdown, autoscaling hibernation, or kernel reboots execute upon reboot.
4. **Fine-Grained Scheduling & Jitter:** Systemd timers support monotonic clocks (`OnBootSec=`, `OnUnitActiveSec=`) and randomized delay (`RandomizedDelaySec=`) to prevent the "thundering herd" problem across large EC2 fleets.

#### Q2 (Deep Database SRE): What is the difference between a logical backup (`pg_dump`) and a physical backup (EBS snapshot / WAL archiving)? In an enterprise architecture, when do you use each?
**Model Answer:**  
- **Logical Backup (`pg_dump`):**
  - *Mechanism:* Reads the catalog and dumps SQL DDL/DML statements (`CREATE TABLE`, `COPY/INSERT`).
  - *Advantages:* Highly portable across PostgreSQL major versions, architectures, and operating systems; allows granular selective table restores; independent of storage engine format.
  - *Disadvantages:* Slower on massive multi-terabyte datasets; locks schema briefly; high CPU and I/O during extraction.
- **Physical Backup (EBS Snapshots / pg_basebackup / WAL-G):**
  - *Mechanism:* Raw block-level or file-level copy of data directory clusters and Write-Ahead Log (WAL) segments.
  - *Advantages:* Enables Point-in-Time Recovery (PITR) to any exact second; instantaneous snapshotting on AWS EBS without database performance degradation; extremely fast restoration for multi-terabyte databases.
  - *Disadvantages:* Tied to specific PostgreSQL major version and operating system architecture.
- *Enterprise Strategy:* Use physical backups (AWS RDS / EBS snapshots + continuous WAL archiving to S3) for low RPO (< 5 minutes) disaster recovery, combined with daily logical backups for compliance, version migrations, and test database seeding.

---

## Sub-Phase 2A.7: Host Firewall Security (UFW) (`linux/firewall/ufw-rules.sh`, `verify-firewall.sh`)

### 1. What Was Implemented
We authored the host-level packet filter automation using Uncomplicated Firewall (UFW) enforcing strict perimeter lockdown:
- **`linux/firewall/ufw-rules.sh`:**
  - `ufw default deny incoming`: All unsolicited inbound packets are dropped by default.
  - `ufw default allow outgoing`: Egress is permitted for package updates, container image pulling, and cloud metadata.
  - `ufw allow 22/tcp`: Permits SSH administrative traffic.
  - `ufw allow 80/tcp`: Permits HTTP traffic (terminating on ALB / Nginx).
  - `ufw allow 443/tcp`: Permits HTTPS TLS-encrypted web traffic.
  - Strictly drops all database ports (PostgreSQL `5432`, Redis `6379`) and non-standard application ports from external access.
- **`linux/firewall/verify-firewall.sh`:**
  - Automated inspection validating active UFW policy status, open listening sockets via `ss -tulpn`, and verification of port restrictions.

---

### 2. Why This Is Critical (AWS & Cloud-Native Production Alignment)

#### AWS Well-Architected Framework: **Security Pillar — Defense-in-Depth (SEC05)**
1. **Defense-in-Depth (Layered Security):**
   - In cloud networking, **AWS Security Groups** act as the primary stateful hypervisor-level perimeter firewall. However, relying *solely* on Security Groups creates a single point of configuration failure (e.g. an engineer inadvertently changing a Security Group rule to `0.0.0.0/0` on port 5432).
   - Host-level firewalls (UFW / `iptables` / `nftables`) implement **Layer 2 of Defense-in-Depth**. Even if an AWS Security Group or Network ACL is misconfigured or relaxed, the Linux OS kernel drops unauthorized packets before they reach application sockets.
2. **Mitigating Lateral Movement:**
   - If an attacker compromises a pod or web container in the same private subnet, a properly hardened host firewall prevents port scanning and lateral exploitation across other node services.
3. **Compliance Requirements:**
   - Industry standards (PCI-DSS Section 1, FedRAMP, CIS Operating System Benchmarks) mandate active host-based packet filtering mechanisms enabled on every compute instance regardless of perimeter cloud firewalls.

---

### 3. Interview Questions & Comprehensive Model Answers

#### Q1 (Cloud Networking / Security): How does a host-level firewall like UFW interact with AWS Security Groups and Network ACLs?
**Model Answer:**  
AWS implements three distinct networking packet filtering boundaries traversed in sequence for any incoming packet:
1. **AWS Network ACL (NACL):** Stateless subnet-level firewall. Evaluates numbered rules in order. First match decides allow or deny. Operates at the VPC router level before packet reaches the virtual network interface (ENI).
2. **AWS Security Group (SG):** Stateful hypervisor-level virtual firewall applied at the Elastic Network Interface (ENI). Only allows rules (no deny rules). Return traffic is automatically allowed. Evaluated before packet enters the guest OS.
3. **Host Firewall (UFW / iptables):** Operates inside the guest Linux kernel (`netfilter`). Enforces OS-level policies on the host network stack.  
*Key Takeaway:* A packet must be allowed by NACL $\to$ allowed by Security Group $\to$ allowed by UFW to successfully establish a socket connection.

#### Q2 (Docker & iptables Pitfall): What critical conflict exists between Docker and UFW, and how do you resolve it in production?
**Model Answer:**  
- **The Issue:** By default, when Docker publishes a port (`-p 8080:8080`), it injects rules directly into the Linux `iptables` `DOCKER` and `PREROUTING` chains. Because `iptables` processes the `PREROUTING` chain *before* the `INPUT` chain where UFW rules reside, **Docker bypasses UFW entirely**. Even if UFW specifies `ufw deny 8080`, external traffic hitting port 8080 will route directly into the Docker container.
- **Production Resolution:**
  1. Bind published container ports exclusively to `127.0.0.1` (`-p 127.0.0.1:8080:8080`), forcing all external inbound traffic to terminate at an authorized host proxy (Nginx or ALB) governed by UFW/SG.
  2. Or configure `/etc/docker/daemon.json` with `{"iptables": false}` and manage routing rules manually.
  3. Or use modern tools like `ufw-docker` which integrates Docker container forwarding into UFW's `AFTER` chains.

---

## Phase 2A Comprehensive Synthesis: Production Readiness & Defense

### Key Metrics & Hardening Verification Matrix

| Hardening Control | Configuration Target | Production Verification Command | Risk Mitigated |
| :--- | :--- | :--- | :--- |
| **SSH Root Lockdown** | `PermitRootLogin no` | `sshd -T \| grep permitrootlogin` | Zero non-attributable administrative access |
| **SSH Password Auth** | `PasswordAuthentication no` | `sshd -T \| grep passwordauthentication` | Eliminates brute-force credential stuffing |
| **Log Directory Mode** | Mode `750` on `/var/log/shoplite` | `ls -ld /var/log/shoplite` | Precludes world-readable/writable log tampering |
| **Log Ingestion ACL** | Exactly 1 rule: `g:ops:r-X` | `getfacl /var/log/shoplite` | Grants Promtail/Ops read without root privilege |
| **DB Backup Timer** | `OnCalendar=*-*-* 02:00:00` | `systemctl list-timers --all` | Daily scheduled RPO point-in-time recovery |
| **DB Backup Catch-up** | `Persistent=true` | `systemctl status shoplite-backup.timer` | Guarantees backup runs even after reboot/downtime |
| **Host Firewall Baseline**| `Default deny incoming` | `ufw status verbose` | Defense-in-depth packet filtering |
| **Permitted Inbound Ports**| Ports 22, 80, 443 only | `ufw status \| grep ALLOW` | Complete isolation of internal DB and Redis ports |

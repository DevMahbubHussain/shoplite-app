# Phase 2C: Ansible Configuration Management & Kubernetes Bootstrapping — Deep Dive & Interview Guide

> **Module:** ShopLite Cloud-Native E-Commerce Platform  
> **Repository:** `shoplite-app`  
> **Phase:** 2C — Ansible Configuration Management & Kubernetes Bootstrapping (Assessment Milestone 2 Completion)  
> **Branch:** `feature/ansible-cluster-bootstrap`

---

## Sub-Phase 2C.1: Inventory & Configuration Architecture (`ansible/ansible.cfg`, `inventory/hosts.yml`)

### 1. What Was Implemented
We established a production-grade, structured Ansible automation framework configured for our live AWS EC2 infrastructure:
- **`ansible/ansible.cfg`:**
  - Configures default inventory path, remote execution user (`ubuntu`), automatic python discovery (`interpreter_python = auto_silent`), and structured YAML stdout formatting.
  - SSH optimizations: `pipelining = True` (reduces SSH round-trips by up to 80% by streaming Python payloads over standard input rather than writing temporary files to remote disk).
  - Strict security privilege escalation: `become = True`, `become_method = sudo`, `become_user = root`.
- **`ansible/inventory/hosts.yml`:**
  - Structured YAML hierarchy with distinct functional groups: `control_plane`, `workers`, and parent meta-group `k8s_cluster`.
  - Wired directly to the live AWS EC2 private IP addresses deployed in Singapore (`ap-southeast-1`):
    - `shoplite-control-plane`: `10.0.10.197` (Instance: `i-054833e78a1497e80`)
    - `shoplite-worker-1`: `10.0.10.9` (Instance: `i-0bc830a92f49d39a4`)
    - `shoplite-worker-2`: `10.0.20.236` (Instance: `i-0b78d3ea2b187f0b4`)
  - Shared cluster variables: `pod_network_cidr: 192.168.0.0/16`, `k8s_version: "1.29"`, `cni_plugin: calico`.

---

### 2. Why This Is Critical (AWS & Cloud-Native Production Alignment)

#### AWS Well-Architected Framework: **Operational Excellence (OPS04, OPS05)**
1. **Infrastructure as Code (IaC) to Configuration Management (CM) Handoff:**
   - Terraform provisions the bare cloud primitives (VPC, Subnets, EC2 instances, EBS volumes).
   - Ansible bridges the gap between raw compute instances and an active container orchestration cluster.
   - Declarative inventories guarantee that any newly launched worker instances can be hardened and joined to the cluster identically without manual SSH configuration.
2. **Elimination of Configuration Drift (Snowflake Servers):**
   - Manual server setup leads to subtle discrepancies across nodes (different kernel versions, missing sysctl flags, mismatched cgroup drivers).
   - Ansible ensures 100% uniformity across all nodes in the fleet.

---

## Sub-Phase 2C.2: Automated OS Hardening Playbook (`ansible/playbooks/harden.yml`)

### 1. What Was Implemented
Automates the operational and security baseline established in Milestone Q3 across all cluster nodes:
- **Identity & Least Privilege:** Creates group `ops` and unprivileged user `deploy`.
- **SSH Lockdown:** Copies hardened `sshd_config` (`PermitRootLogin no`, `PasswordAuthentication no`, `PubkeyAuthentication yes`) and verifies syntax with `sshd -t -f` before restarting.
- **Log Permissions & POSIX ACLs:** Creates `/var/log/shoplite` owned by `root:ops` with mode `750` and applies exactly one POSIX ACL rule (`setfacl -R -m g:ops:r-X`).
- **Host Firewall (UFW):** Sets default deny incoming, permits ports `22`, `80`, `443`, and allows all internal VPC traffic across `10.0.0.0/16` for intra-cluster communication.
- **Automated Backup Systemd Units:** Deploys `shoplite-backup.sh`, `shoplite-backup.service`, and starts `shoplite-backup.timer`.

---

## Sub-Phase 2C.3: Container Runtime (containerd) Playbook (`ansible/playbooks/containerd.yml`)

### 1. What Was Implemented
Installs and tunes the official CNCF `containerd` container runtime for production Kubernetes compatibility:
- **Kernel Modules:** Loads `overlay` and `br_netfilter` into the Linux kernel and persists them in `/etc/modules-load.d/k8s.conf`.
- **Networking Sysctl Parameters:** Configures `/etc/sysctl.d/k8s.conf` with:
  - `net.bridge.bridge-nf-call-iptables = 1`
  - `net.bridge.bridge-nf-call-ip6tables = 1`
  - `net.ipv4.ip_forward = 1`
- **Memory Management:** Disables Linux swap via `swapoff -a` and comments out swap mounts in `/etc/fstab`.
- **containerd Cgroup Driver Alignment:**
  - Installs `containerd.io` from official Docker apt repositories.
  - Generates default `config.toml` and modifies `SystemdCgroup = true` under `plugins."io.containerd.grpc.v1.cri".containerd.runtimes.runc.options`.

---

### 2. Why This Is Critical (AWS & Cloud-Native Production Alignment)

#### AWS Well-Architected Framework: **Reliability & Performance Efficiency (REL02, PERF05)**
1. **The `SystemdCgroup = true` Mandate:**
   - Linux uses Control Groups (cgroups) to enforce resource boundaries (CPU and memory limits) on containers.
   - Ubuntu uses `systemd` as its initial system daemon. When a system uses systemd as the init system, there should only be **one single cgroup manager** on the entire host: systemd.
   - If containerd or runc uses the legacy `cgroupfs` manager while the host uses `systemd`, two separate entities allocate and manage cgroups. Under high memory pressure, this causes resource descriptor fragmentation, memory metric reporting drift, and erratic container kills by the Linux OOM killer.
2. **Why Swap Disabling is Mandatory:**
   - Kubernetes' scheduling algorithm assumes that a pod's memory request and limit are backed strictly by physical RAM.
   - If swap is enabled, the kernel may swap container memory out to disk when memory pressure spikes. This destroys performance predictability, increases latency tenfold, and causes Kubernetes quality-of-service (QoS) guarantees (`Guaranteed`, `Burstable`, `BestEffort`) to fail.

---

## Sub-Phase 2C.4 & 2C.5: Kubernetes Bootstrap & Kubeconfig Retrieval (`k8s-cluster.yml`, `fetch-kubeconfig.yml`)

### 1. What Was Implemented
- **Package Pinning:** Installs `kubelet`, `kubeadm`, `kubectl` (`1.29`) and locks them with `apt-mark hold` to prevent uncontrolled apt upgrades from breaking cluster compatibility.
- **Control Plane Initialization:**
  - Idempotent `kubeadm init` with `--pod-network-cidr=192.168.0.0/16` and `--apiserver-advertise-address=10.0.10.197`.
  - Configures admin kubeconfig for `root` and `ubuntu` users.
  - Deploys Project Calico CNI manifest.
- **Worker Node Joining:**
  - Generates cluster join token on control plane.
  - Dynamically passes the join token to worker nodes and executes `kubeadm join`.
- **Kubeconfig Retrieval (`fetch-kubeconfig.yml`):**
  - Fetches `/etc/kubernetes/admin.conf` directly to operator workstation with mode `0600` for remote cluster control.

---

### 3. Interview Questions & Comprehensive Model Answers

#### Q1 (Kubernetes Internals): Why does `kubelet` fail to start if the container runtime cgroup driver does not match the system cgroup driver?
**Model Answer:**  
Kubernetes nodes require a consistent resource accounting tree under `/sys/fs/cgroup`. On modern Linux distributions (Ubuntu, RHEL 8+, Debian), `systemd` manages cgroup hierarchies. If `kubelet` is configured to use the `systemd` cgroup driver while `containerd` is configured with `cgroupfs`, kubelet will attempt to query pod cgroup nodes created by containerd and find them missing or structured improperly under the systemd slice hierarchy (`/sys/fs/cgroup/system.slice/...`). Kubelet detects this dual-cgroup-manager conflict during startup health checks and aborts with fatal error `misconfigured cgroup driver`.

#### Q2 (Networking & CNI): How does Calico CNI route traffic between pods on different worker nodes in an AWS VPC?
**Model Answer:**  
Calico utilizes the BGP (Border Gateway Protocol) routing protocol and Linux iptables:
1. **Felix & BIRD:** On each node, the Calico agent (`Felix`) writes local routing table entries, and the BIRD routing daemon peers with other nodes over TCP port 179 to advertise pod CIDR subnet allocations (e.g. `192.168.1.0/24` on Node 1, `192.168.2.0/24` on Node 2).
2. **Encapsulation (VXLAN or IP-in-IP):** In AWS VPCs where cross-subnet traffic traverses AWS routers that only know VPC CIDRs (`10.0.0.0/16`), Calico encapsulates the pod IP packet inside an outer IPv4 packet (IP-in-IP protocol 4 or VXLAN UDP port 4789).
3. **Decapsulation:** When the outer packet reaches the destination EC2 node, the Linux kernel decapsulates the packet and delivers the raw inner packet to the target container's `veth` network interface.

#### Q3 (Idempotency in Ansible): How do you ensure that `kubeadm init` and `kubeadm join` in Ansible are strictly idempotent and do not fail on repeated runs?
**Model Answer:**  
`kubeadm init` will fail if run on an already initialized control plane (`/etc/kubernetes/admin.conf` already exists), and `kubeadm join` will fail if a node has already joined (`/etc/kubernetes/kubelet.conf` already exists).  
To achieve idempotency:
1. Use `ansible.builtin.stat` before the command to inspect the presence of `/etc/kubernetes/admin.conf` on control plane and `/etc/kubernetes/kubelet.conf` on workers.
2. Register the stat result as a variable (`register: kubelet_conf_check`).
3. Add conditional guard `when: not kubelet_conf_check.stat.exists` to the command task.  
This guarantees that subsequent runs skip the bootstrap tasks without failing, preserving existing cluster state.

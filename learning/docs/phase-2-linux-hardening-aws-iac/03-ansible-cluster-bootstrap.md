# Phase 2.3: Ansible Automated Node Bootstrapping & Cluster Provisioning

> **Module:** ShopLite Cloud-Native Platform  
> **Key Concepts:** Ansible Playbooks, Containerd Runtime, Kernel Modules (`overlay`, `br_netfilter`), Kubeadm Bootstrap, CNI Networking, Kubeconfig Secure Fetch  

---

## 1. Key Learning Points (Simple English)

- **Idempotent Configuration Management:** Ansible ensures that re-running playbooks does not break existing configurations or reboot running services unnecessarily.
- **Ordered Playbook Execution Pipeline:**
  1. `harden.yml`: Provisions the `ops` group, `deploy` user, SSH daemon hardening, directory permissions, and UFW firewall.
  2. `containerd.yml`: Loads required Linux kernel modules (`overlay`, `br_netfilter`), sets `sysctl` network bridges (`net.bridge.bridge-nf-call-iptables = 1`, `net.ipv4.ip_forward = 1`), and installs `containerd` with `SystemdCgroup = true`.
  3. `k8s-cluster.yml`: Initializes the control plane via `kubeadm init`, deploys the Calico/Flannel CNI network plugin, extracts the cluster join token, and executes `kubeadm join` on worker nodes.
  4. `fetch-kubeconfig.yml`: Securely fetches `/etc/kubernetes/admin.conf` from the control plane to the operator's workstation with mode `0600`.

---

## 2. বাংলা সারাংশ ও মূল ধারণা (Bengali Summary)

- **অ্যানসিবল অটোমেশন (Ansible):** ম্যানুয়ালি সার্ভারে ঢুকে সফটওয়্যার ইনস্টল না করে কোড দিয়ে স্বয়ংক্রিয়ভাবে সার্ভার কনফিগার করার টুল।
- **কার্নেল মডিউল ও কন্টেইনারডি:** কিউবারনেটিসের কনটেইনার নেটওয়ার্কিং ঠিকমতো কাজ করার জন্য লিনাক্সের `overlay` এবং `br_netfilter` কার্নেল মডিউল অন করতে হয় এবং কন্টেইনার রানটাইম হিসেবে `containerd` কনফিগার করা হয়।
- **কিউবএডম ক্লাস্টার বুটস্ট্র্যাপ (`kubeadm`):** কন্ট্রোল প্লেনে `kubeadm init` কমান্ড চালিয়ে ক্লাস্টার ইনিশিয়ালাইজ করা হয়, সিএনআই (Calico/Flannel) নেটওয়ার্ক বসানো হয় এবং ওয়ার্কার নোডগুলোকে ক্লাস্টারে জয়েন করানো হয়।

---

## 3. DevOps & Cloud Architect Interview Q&A

### Q1: Why must `SystemdCgroup` be set to `true` in containerd for Kubernetes clusters?
**Model Answer (English):**  
On Linux systems using `systemd` as the init system, there should be a single cgroup manager. When both `systemd` and `cgroupfs` attempt to manage cgroups independently, resources (CPU/memory constraints) can be double-counted or destabilized under resource pressure, causing unpredictable OOM kills. Setting `SystemdCgroup = true` aligns containerd with Kubelet's `systemd` cgroup driver, ensuring stable node resource accounting.

**বাংলা ব্যাখ্যা:**  
লিনাক্সে রিসোর্স (সিপিইউ ও মেমোরি) লিমিট ম্যানেজ করার জন্য `systemd` কাজ করে। ডকার বা কন্টেইনারডি যদি আলাদা সিগ্রুপ ড্রাইভার চালায়, তবে ক্লাস্টারে মেমোরি ব্যবস্থাপনায় দ্বন্দ্ব তৈরি হয় এবং সার্ভার ক্র্যাশ করতে পারে। তাই উভয়ের ড্রাইভার এক রাখা বাধ্যতামূলক।

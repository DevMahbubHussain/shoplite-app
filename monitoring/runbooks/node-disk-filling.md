# Runbook: NodeDiskFilling

> **Alert Name:** `NodeDiskFilling`  
> **Severity:** Warning  
> **Tier:** Infrastructure (EC2 / Kubernetes Nodes)  
> **Evaluation Window:** 5 minutes  
> **Threshold:** Available disk space on root filesystem (`/`) is $< 15\%$ ($> 85\%$ utilized)

---

## 1. Incident Overview & Impact
- **Description:** Available disk storage on the root mount point (`/`) of one or more Kubernetes cluster nodes has dropped below 15%.
- **Business Impact:** If disk space reaches $100\%$, the Kubernetes kubelet will initiate automated pod evictions (`DiskPressure` condition), containerd will fail to pull images or create container write layers, and node logging / OS daemons will hang or crash.
- **Probable Causes:**
  1. Excessive container log accumulation in `/var/log/pods/` due to verbose logging.
  2. Unpruned dangling container images in containerd storage (`/var/lib/containerd/`).
  3. Ephemeral volumes (`emptyDir`) or temporary files written without size limits.
  4. Core dumps or unrotated systemd journal logs.

---

## 2. Step-by-Step Triage & Diagnosis

### Step 1: Identify Affected Node via Prometheus
Run in Prometheus Expression Browser to identify which node is running out of disk:
```promql
# List percentage of available disk space by node instance
(node_filesystem_avail_bytes{mountpoint="/"} / node_filesystem_size_bytes{mountpoint="/"}) * 100
```

### Step 2: Establish SSM Session or SSH to the Affected Node
Connect securely to the target EC2 node via AWS Systems Manager Session Manager:
```bash
aws ssm start-session --target <instance-id>
```

### Step 3: Inspect Filesystem Usage via Terminal
```bash
# Check filesystem capacity
df -h /

# Locate the top 10 largest directories on the node
sudo du -xh / 2>/dev/null | sort -rh | head -n 10
```

### Step 4: Inspect Container Logs & containerd Image Cache
Check `/var/log/pods` and `/var/lib/containerd`:
```bash
# Check pod log directory size
sudo du -sh /var/log/pods

# Check containerd image cache size
sudo du -sh /var/lib/containerd
```

---

## 3. Remediation & Mitigation

### Step 1: Prune Unused Container Images
Trigger containerd or crictl image cleanup:
```bash
# Remove dangling/unused container images
sudo crictl rmi --prune
```

### Step 2: Clean Truncated Pod Logs
If an application was spamming stdout logs, truncate oversized log files:
```bash
# Find and truncate logs larger than 100MB
sudo find /var/log/pods -name "*.log" -size +100M -exec truncate -s 0 {} \;
```

### Step 3: Vacuum systemd Journal Logs
Reduce journald disk consumption:
```bash
sudo journalctl --vacuum-size=200M
```

### Step 4: Long-Term EBS Volume Expansion (if genuine workload growth)
If legitimate workload growth caused disk utilization:
1. Modify EBS volume size via AWS CLI or Terraform:
   ```bash
   aws ec2 modify-volume --volume-id <vol-id> --size 50
   ```
2. Grow partition and filesystem on the EC2 instance without rebooting:
   ```bash
   sudo growpart /dev/xvda 1
   sudo resize2fs /dev/xvda1   # (or xfs_growfs / for XFS)
   ```

---

## 4. Resolution Verification
1. Verify `df -h /` shows $> 30\%$ available space.
2. Confirm the Kubernetes node does not report `DiskPressure`:
   ```bash
   kubectl describe node <node-name> | grep -A 5 "Conditions:"
   ```
3. Verify Alertmanager reports `NodeDiskFilling` as resolved.

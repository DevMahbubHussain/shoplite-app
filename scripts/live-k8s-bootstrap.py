#!/usr/bin/env python3
"""
ShopLite Live Kubernetes Cluster Bootstrapper
Executes remote configuration via AWS Systems Manager (SSM) Run Command across:
- Control Plane: i-054833e78a1497e80 (10.0.10.197)
- Worker 1:      i-0bc830a92f49d39a4 (10.0.10.9)
- Worker 2:      i-0b78d3ea2b187f0b4 (10.0.20.236)
"""

import sys
import time
import boto3

REGION = "ap-southeast-1"
CP_INSTANCE_ID = "i-054833e78a1497e80"
WORKER_1_ID = "i-0bc830a92f49d39a4"
WORKER_2_ID = "i-0b78d3ea2b187f0b4"
ALL_INSTANCES = [CP_INSTANCE_ID, WORKER_1_ID, WORKER_2_ID]

ssm = boto3.client("ssm", region_name=REGION)


def run_ssm_command(instance_ids: list[str], commands: list[str], comment: str) -> dict[str, str]:
    print(f"\n[SSM] Sending command: {comment} to {instance_ids}...")
    response = ssm.send_command(
        InstanceIds=instance_ids,
        DocumentName="AWS-RunShellScript",
        Comment=comment,
        Parameters={"commands": commands, "executionTimeout": ["600"]},
    )
    command_id = response["Command"]["CommandId"]
    print(f"[SSM] Command ID: {command_id}. Awaiting completion...")

    results = {}
    for instance_id in instance_ids:
        while True:
            try:
                invocation = ssm.get_command_invocation(
                    CommandId=command_id,
                    InstanceId=instance_id,
                )
                status = invocation["Status"]
                if status in ["Success", "Failed", "Cancelled", "TimedOut"]:
                    stdout = invocation.get("StandardOutputContent", "")
                    stderr = invocation.get("StandardErrorContent", "")
                    print(f" -> Instance {instance_id}: Status = {status}")
                    if status != "Success":
                        print(f"    ERROR output:\n{stderr}\n{stdout}")
                    results[instance_id] = stdout
                    break
            except Exception:
                pass
            time.sleep(3)

    return results


def main():
    print("==========================================================")
    print(" Starting ShopLite Live Kubernetes Cluster Bootstrap")
    print(f" Region: {REGION}")
    print(f" Control Plane: {CP_INSTANCE_ID}")
    print(f" Workers:       {WORKER_1_ID}, {WORKER_2_ID}")
    print("==========================================================")

    # Step 1: Install containerd, kernel tuning, and Kubernetes packages across all 3 nodes
    step1_commands = [
        "set -euo pipefail",
        "swapoff -a",
        "sed -i '/ swap / s/^/#/' /etc/fstab",
        "cat <<'EOF' > /etc/modules-load.d/k8s.conf",
        "overlay",
        "br_netfilter",
        "EOF",
        "modprobe overlay",
        "modprobe br_netfilter",
        "cat <<'EOF' > /etc/sysctl.d/k8s.conf",
        "net.bridge.bridge-nf-call-iptables  = 1",
        "net.bridge.bridge-nf-call-ip6tables = 1",
        "net.ipv4.ip_forward                 = 1",
        "EOF",
        "sysctl --system",
        "apt-get update -y",
        "apt-get install -y apt-transport-https ca-certificates curl gnupg lsb-release acl socat conntrack",
        "groupadd -f ops && id -u deploy &>/dev/null || useradd -m -s /bin/bash -g ops deploy",
        "mkdir -p /var/log/shoplite && chown -R root:ops /var/log/shoplite && chmod 750 /var/log/shoplite",
        "setfacl -R -m g:ops:r-X /var/log/shoplite",
        "mkdir -p /etc/apt/keyrings",
        "curl -fsSL https://download.docker.com/linux/ubuntu/gpg | gpg --dearmor -o /etc/apt/keyrings/docker.gpg --yes",
        "echo \"deb [arch=amd64 signed-by=/etc/apt/keyrings/docker.gpg] https://download.docker.com/linux/ubuntu $(lsb_release -cs) stable\" > /etc/apt/sources.list.d/docker.list",
        "apt-get update -y",
        "apt-get install -y containerd.io",
        "mkdir -p /etc/containerd",
        "containerd config default > /etc/containerd/config.toml",
        "sed -i 's/SystemdCgroup = false/SystemdCgroup = true/g' /etc/containerd/config.toml",
        "systemctl restart containerd",
        "systemctl enable containerd",
        "curl -fsSL https://pkgs.k8s.io/core:/stable:/v1.29/deb/Release.key | gpg --dearmor -o /etc/apt/keyrings/kubernetes-apt-keyring.gpg --yes",
        "echo \"deb [signed-by=/etc/apt/keyrings/kubernetes-apt-keyring.gpg] https://pkgs.k8s.io/core:/stable:/v1.29/deb/ /\" > /etc/apt/sources.list.d/kubernetes.list",
        "apt-get update -y",
        "apt-get install -y kubelet kubeadm kubectl",
        "apt-mark hold kubelet kubeadm kubectl",
        "echo '=== NODE PREREQUISITES READY ==='",
    ]

    print("\n--- [Step 1/4] Installing containerd and Kubernetes on all 3 nodes ---")
    run_ssm_command(ALL_INSTANCES, step1_commands, "Step 1: Container runtime & K8s installation")

    # Step 2: Initialize Control Plane
    step2_commands = [
        "set -euo pipefail",
        "if [ ! -f /etc/kubernetes/admin.conf ]; then",
        "  kubeadm init --pod-network-cidr=192.168.0.0/16 --apiserver-advertise-address=10.0.10.197 --node-name=shoplite-control-plane",
        "  mkdir -p /root/.kube /home/ubuntu/.kube",
        "  cp -f /etc/kubernetes/admin.conf /root/.kube/config",
        "  cp -f /etc/kubernetes/admin.conf /home/ubuntu/.kube/config",
        "  chown -R ubuntu:ubuntu /home/ubuntu/.kube",
        "  kubectl apply -f https://raw.githubusercontent.com/projectcalico/calico/v3.27.0/manifests/calico.yaml",
        "fi",
        "kubeadm token create --print-join-command",
    ]

    print("\n--- [Step 2/4] Initializing Kubernetes Control Plane & Calico CNI ---")
    cp_results = run_ssm_command([CP_INSTANCE_ID], step2_commands, "Step 2: kubeadm init on control plane")
    cp_output = cp_results[CP_INSTANCE_ID]

    # Extract join command
    join_cmd = None
    for line in cp_output.splitlines():
        if "kubeadm join" in line:
            join_cmd = line.strip()
            break

    if not join_cmd:
        print("ERROR: Could not parse kubeadm join command!")
        sys.exit(1)

    print(f"\n[SSM] Extracted Worker Join Command:\n{join_cmd}")

    # Step 3: Join Workers to the Cluster
    step3_commands = [
        "set -euo pipefail",
        "if [ ! -f /etc/kubernetes/kubelet.conf ]; then",
        f"  {join_cmd}",
        "else",
        "  echo 'Worker already joined'",
        "fi",
    ]

    print("\n--- [Step 3/4] Joining Worker Nodes to Cluster ---")
    run_ssm_command([WORKER_1_ID, WORKER_2_ID], step3_commands, "Step 3: kubeadm join on workers")

    # Step 4: Verify Cluster Nodes Status
    print("\n--- [Step 4/4] Verifying Live Cluster State from Control Plane ---")
    time.sleep(15)  # Allow CNI and node registration to settle
    verify_commands = [
        "kubectl get nodes -o wide",
        "kubectl get pods -A",
    ]
    status_results = run_ssm_command([CP_INSTANCE_ID], verify_commands, "Step 4: Check cluster node status")
    print("\n================ CLUSTER NODE STATUS ================")
    print(status_results[CP_INSTANCE_ID])
    print("=====================================================")


if __name__ == "__main__":
    main()

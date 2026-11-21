# ShopLite — AWS Live Deployment Runbook

**Owner:** ShopLite Platform Engineering
**Last validated:** 2026-11-21 (infrastructure provisioned and torn down on a managed sandbox account)
**Applies to:** Deploying the ShopLite platform to live AWS infrastructure (EC2 + kubeadm + Helm + GitOps) from a Windows workstation with WSL2.

---

## 1. Overview

```
Internet
   │
   ▼
Application Load Balancer (public, 2 AZ)
   │  (NodePort 30000–32767 → worker SG)
   ▼
ingress-nginx ──► web / catalog-api pods (namespace: shoplite)
                     │
        ┌────────────┴───────────┐
        ▼                        ▼
   PostgreSQL (StatefulSet)  Redis
        ▲                        ▲
        └────── order-worker ────┘

Admin access: AWS SSM Session Manager ONLY (no public IPs, no SSH keys)
Egress:       Private subnets → NAT Gateway (1) → IGW
State:        Terraform remote state in S3, locking in DynamoDB
```

- Region: `ap-southeast-1` (Singapore), 2 AZs (`ap-southeast-1a`, `ap-southeast-1b`)
- Subnets: `10.0.1.0/24`, `10.0.2.0/24` (public — ALB + NAT) · `10.0.10.0/24`, `10.0.20.0/24` (private — Kubernetes nodes)
- Compute: 1 control plane + 2 workers, `t3.medium` (4 GB — kubeadm minimum), Ubuntu 22.04 LTS
- Node IAM role: `AmazonSSMManagedInstanceCore` + `AmazonEC2ContainerRegistryReadOnly`

---

## 2. Toolchain Requirements

| Tool | Version | Host | Notes |
| :--- | :--- | :--- | :--- |
| AWS CLI | 2.28.16 | Windows | credentials in `~/.aws/credentials` |
| Terraform | 1.13.2 | Windows | invoke with `-chdir` |
| kubectl | 1.34.1 | Windows | |
| Helm | 4.3.1 | Windows | |
| Docker Desktop | WSL2 backend | Windows | image builds + ECR push |
| Ansible | core 2.21.6 | WSL Ubuntu 24.04 | `~/.local/bin/ansible` |
| amazon.aws collection | bundled | WSL | provides the `aws_ssm` connection plugin |
| boto3 | 1.44.9 | WSL | required by the SSM connection plugin |
| session-manager-plugin | 1.2.896.0 | WSL | `~/.local/bin/session-manager-plugin` |

The deploying IAM user requires permissions for EC2, ELBv2, S3, DynamoDB, IAM (roles/profiles/policies), ECR, Budgets, and SSM — including `ssm:StartSession` and the `ssmmessages:*` actions that back it.

### 2.1 WSL ↔ Windows credentials

Ansible's SSM plugin authenticates through boto3, which reads the WSL-side `~/.aws`. Sync it once:

```bash
# inside WSL
mkdir -p ~/.aws
cp /mnt/c/Users/<YOU>/.aws/credentials ~/.aws/credentials
cp /mnt/c/Users/<YOU>/.aws/config ~/.aws/config 2>/dev/null
chmod 600 ~/.aws/*
```

Confirm with `aws sts get-caller-identity` returning the expected account.

---

## 3. Terraform State Backend

The root backend (`terraform/backend.tf`) points at S3 + DynamoDB. Bucket names are globally unique and the configured names embed the account ID, so each new AWS account needs its own renamed bucket.

Update these files when moving accounts (old ID → new ID):

1. `terraform/bootstrap/main.tf` — `state_bucket_name` default
2. `terraform/backend.tf` — `bucket`
3. `helm/shoplite/values.yaml` — the three ECR `repository:` fields

```bash
cd terraform/bootstrap
terraform init
terraform apply -auto-approve
# creates the S3 bucket (versioned, SSE-S3, public access blocked) and the DynamoDB lock table

cd ..
terraform init -reconfigure
# -reconfigure starts a fresh remote state; never -migrate-state across accounts
```

Validated values: bucket `shoplite-tfstate-904907793701`, table `shoplite-tflocks`.

---

## 4. Infrastructure Deployment

```bash
terraform -chdir=terraform plan  -no-color -input=false   # review first
terraform -chdir=terraform apply -auto-approve -no-color -input=false
```

The apply takes 5–10 minutes; the NAT Gateway and ALB dominate the duration.

Outputs from the 2026-11-21 deployment:

| Output | Value |
| :--- | :--- |
| VPC | `vpc-010dfd8f80fc63760` |
| Control plane | `i-0428f398a5508c587` @ `10.0.10.5` |
| Worker 1 | `i-090c9fe3973ffa5ff` @ `10.0.10.157` |
| Worker 2 | `i-068002d9a8b4ffd01` @ `10.0.20.225` |
| NAT EIP | `13.250.174.46` |
| ALB DNS | `shoplite-prod-alb-1654679591.ap-southeast-1.elb.amazonaws.com` |
| ECR URLs | `904907793701.dkr.ecr.ap-southeast-1.amazonaws.com/shoplite-{web,catalog-api,order-worker}` |
| SSM instance profile | `shoplite-prod-node-profile` |

Verify instances are healthy before continuing:

```bash
aws ec2 describe-instance-status --instance-ids <cp-id> \
  --query "InstanceStatuses[].{state:InstanceState.Name,sys:InstanceStatus.Status}"
```

---

## 5. Node Access Validation (SSM)

Nodes carry no public IPs and no SSH keys; all administration happens over SSM. Allow 2–3 minutes after boot for agent registration.

```bash
aws ssm describe-instance-information \
  --query "InstanceInformationList[].{id:InstanceId,ping:PingStatus,agent:AgentVersion,last:LastPingDateTime}"
```

Check that `LastPingDateTime` is close to the current time — a stale timestamp alongside `Online` means cached data (see Troubleshooting T-1).

Exercise the execution channel:

```bash
CMD_ID=$(aws ssm send-command --instance-ids <cp-id> \
  --document-name AWS-RunShellScript \
  --parameters commands="hostname && uptime" \
  --query "Command.CommandId" --output text)
sleep 12
aws ssm list-command-invocations --command-id "$CMD_ID" --details \
  --query "CommandInvocations[].{status:Status,output:CommandPlugins[0].Output}"
```

Both RunCommand and Session Manager must work before running Ansible. If they do not, resolve per Troubleshooting T-2 before proceeding.

---

## 6. Cluster Bootstrap (Ansible over SSM)

### 6.1 Ansible setup inside WSL

Ubuntu 24.04 ships no pip, and apt installs need an interactive sudo password. The following installs the full toolchain without root:

```bash
curl -sS https://bootstrap.pypa.io/get-pip.py -o ~/get-pip.py
python3 ~/get-pip.py --user --break-system-packages      # PEP 668 override
~/.local/bin/pip install --user --break-system-packages ansible boto3

# Session Manager plugin: extract the binary from the official .deb
curl -sS -o ~/smp.deb \
  https://s3.amazonaws.com/session-manager-downloads/plugin/latest/ubuntu_64bit/session-manager-plugin.deb
dpkg-deb -x ~/smp.deb ~/smp-extract
cp ~/smp-extract/usr/local/sessionmanagerplugin/bin/session-manager-plugin ~/.local/bin/
chmod +x ~/.local/bin/session-manager-plugin
rm -rf ~/smp.deb ~/smp-extract
```

Verify: `~/.local/bin/ansible --version`, `~/.local/bin/session-manager-plugin --version`, and `ansible-doc -t connection -l | grep ssm`.

> **WSL note:** `/tmp` is wiped whenever the WSL VM idles out. Multi-step operations touching `/tmp` must run as a single chained command, or should use `$HOME` paths.

### 6.2 Inventory configuration

Each node entry carries its `instance_id` (from `terraform output`). Group vars wire the SSM transport in `ansible/inventory/hosts.yml`:

```yaml
k8s_cluster:
  vars:
    ansible_connection: amazon.aws.aws_ssm
    ansible_aws_ssm_region: ap-southeast-1
    ansible_aws_ssm_bucket_name: <artifacts-bucket>
    ansible_aws_ssm_plugin: /home/<you>/.local/bin/session-manager-plugin
```

Create the artifacts bucket used for Ansible file transfer:

```bash
aws s3api create-bucket --bucket shoplite-ansible-artifacts-<account> \
  --region ap-southeast-1 \
  --create-bucket-configuration LocationConstraint=ap-southeast-1
aws s3api put-public-access-block --bucket shoplite-ansible-artifacts-<account> \
  --public-access-block-configuration "BlockPublicAcls=true,IgnorePublicAcls=true,BlockPublicPolicy=true,RestrictPublicBuckets=true"
```

> **Note:** WSL mounts NTFS drives as world-writable, so Ansible will not auto-load `ansible.cfg` from `/mnt/*`. Always pass the inventory explicitly with `-i inventory/hosts.yml`.

### 6.3 Deployment sequence

```bash
cd <repo>/ansible   # inside WSL

ansible k8s_cluster -i inventory/hosts.yml -m ping
ansible-playbook -i inventory/hosts.yml playbooks/harden.yml        # OS hardening
ansible-playbook -i inventory/hosts.yml playbooks/containerd.yml    # container runtime
ansible-playbook -i inventory/hosts.yml playbooks/k8s-cluster.yml   # kubeadm v1.29 + Calico v3.27
ansible-playbook -i inventory/hosts.yml playbooks/fetch-kubeconfig.yml

export KUBECONFIG=<repo>/ansible/kubeconfig
kubectl get nodes -o wide   # 1 control-plane + 2 workers, all Ready
```

Typical per-node durations: harden 2–3 min, containerd ~2 min, k8s-cluster 6–8 min.

---

## 7. Application Delivery

### 7.1 Push images to ECR

```bash
AWS_ACCOUNT=<account>; REGION=ap-southeast-1
aws ecr get-login-password --region $REGION | \
  docker login --username AWS --password-stdin $AWS_ACCOUNT.dkr.ecr.$REGION.amazonaws.com

for svc in web catalog-api order-worker; do
  docker build -t $AWS_ACCOUNT.dkr.ecr.$REGION.amazonaws.com/shoplite-$svc:latest services/$svc
  docker push $AWS_ACCOUNT.dkr.ecr.$REGION.amazonaws.com/shoplite-$svc:latest
done
```

### 7.2 Helm and ArgoCD

The API server port (6443) is reachable only from worker security groups, so tunnel it through SSM for local kubectl:

```bash
aws ssm start-session --target <cp-id> \
  --document-name AWS-StartPortForwardingSessionToRemoteHost \
  --parameters '{"host":["10.0.10.5"],"portNumber":["6443"],"localPortNumber":["6443"]}'
```

```bash
kubectl apply -n argocd -f https://raw.githubusercontent.com/argoproj/argo-cd/stable/manifests/install.yaml
kubectl apply -f <shoplite-gitops>/argocd/apps/shoplite-dev-app.yaml
kubectl get pods,svc,ingress,hpa,pdb -n shoplite
```

### 7.3 End-to-end verification through the ALB

```bash
ALB=shoplite-prod-alb-<id>.ap-southeast-1.elb.amazonaws.com
curl -s http://$ALB/                          # web UI
curl -s http://$ALB/api/products              # ≥ 10 seeded products
curl -s -X POST http://$ALB/api/orders \
     -H "Content-Type: application/json" \
     -d '{"product_id":1,"quantity":2}'       # 201 Created, status PENDING
# poll GET /api/orders/{id} → PROCESSING → COMPLETED
curl -s http://$ALB/api/metrics | grep orders_
```

---

## 8. Teardown

```bash
# 1. Root stack (VPC, EC2, ALB, ECR, NAT, budgets) — 5–10 minutes
terraform -chdir=terraform destroy -auto-approve -no-color -input=false

# 2. State backend: empty the versioned bucket, remove bucket + lock table
aws s3api delete-objects --bucket shoplite-tfstate-<account> \
  --delete "$(aws s3api list-object-versions --bucket shoplite-tfstate-<account> \
  --query '{Objects: Versions[].{Key:Key,VersionId:VersionId}}')"
aws s3 rb s3://shoplite-tfstate-<account> --region ap-southeast-1
aws dynamodb delete-table --table-name shoplite-tflocks --region ap-southeast-1

# 3. Ansible artifacts bucket
aws s3api delete-objects --bucket shoplite-ansible-artifacts-<account> \
  --delete "$(aws s3api list-object-versions --bucket shoplite-ansible-artifacts-<account> \
  --query '{Objects: Versions[].{Key:Key,VersionId:VersionId}}')"
aws s3 rb s3://shoplite-ansible-artifacts-<account> --region ap-southeast-1

# 4. Confirm nothing billable remains
aws ec2 describe-instances    --filters Name=instance-state-name,Values=running --query "length(Reservations)"
aws ec2 describe-nat-gateways --filter Name=state,Values=available --query "length(NatGateways)"
aws elbv2 describe-load-balancers --query "length(LoadBalancers)"
aws ecr describe-repositories --query "length(repositories)"
aws s3 ls
aws dynamodb list-tables --region ap-southeast-1
aws iam list-roles --query "Roles[?contains(RoleName,'shoplite')].RoleName"
```

Every count must return `0` / empty. The bootstrap stack protects its bucket with `lifecycle.prevent_destroy`, which is why step 2 empties and removes the bucket through the CLI rather than `terraform destroy`.

---

## 9. Cost Model (ap-southeast-1, on-demand)

| Resource | Rate | Daily |
| :--- | :--- | :--- |
| 3× t3.medium | ~$0.0416/hr each | ~$3.00 |
| NAT Gateway | ~$0.045/hr + data | ~$1.10 |
| ALB | ~$0.0225/hr + LCU | ~$0.60 |
| EBS 3× 30 GB gp3 | ~$0.08/GB-mo | ~$0.25 |
| **Total (idle cluster)** | | **~$5/day** |

A single-day deployment cycle costs under $10; the stack left running costs $80–120/month. Teardown (Section 8) is part of every deployment cycle.

---

## 10. Troubleshooting

### T-1 — SSM reports `Online` but the timestamp is stale

**Symptom:** `describe-instance-information` shows `Online`, `LastPingDateTime` is an hour old, commands stay `Pending`.

**Cause:** SSM caches registration state; an agent can silently stop heartbeating while its registry entry persists.

**Resolution:** compare `LastPingDateTime` against the wall clock before trusting `Online`. `aws ec2 reboot-instances` restores the agent within about two minutes.

### T-2 — RunCommand `Pending` and StartSession `TargetNotConnected` while heartbeat is healthy

**Symptom:** all three agents heartbeat normally, EC2 status checks pass, boot logs are clean, yet `send-command` never executes and `start-session` fails with `TargetNotConnected` on every node.

**Diagnosis performed (2026-11-21):**

1. Node IAM role intact — exactly `AmazonSSMManagedInstanceCore` + `AmazonEC2ContainerRegistryReadOnly`, no inline policies, no permissions boundary; IAM is not the cause
2. `https://ssmmessages.ap-southeast-1.amazonaws.com` reachable (TLS OK) — the service itself is up
3. Reboots restore heartbeats but not the execution channels — the condition is persistent, not a crash loop
4. Heartbeat traffic uses `ssm.*`; both RunCommand delivery and sessions use `ssmmessages.*` — the split points at that data plane

**Cause:** the managed sandbox account used for this deployment enforces an organization policy that restricts `ssmmessages:*` for instance roles. This applies to every account issued by that platform and cannot be lifted from a member account.

**Resolution:** none available on the platform-issued accounts; SSM-based administration cannot be used there. On a standard AWS account (no organization restrictions) this failure mode does not occur, and this runbook applies end-to-end. Validate the execution channel (Section 5) immediately after `terraform apply` on any new account before investing further deployment effort.

### T-3 — Ansible inventory appears empty ("Could not match supplied host pattern")

**Cause:** Ansible refuses to auto-load `ansible.cfg` from world-writable directories; all NTFS mounts under `/mnt/*` are world-writable.

**Resolution:** pass the inventory explicitly: `-i inventory/hosts.yml`.

### T-4 — pip refuses to install in WSL (PEP 668 externally-managed environment)

**Resolution:** `python3 get-pip.py --user --break-system-packages`, then `pip install --user --break-system-packages ...`.

### T-5 — `terraform init` prompts to migrate state after a backend change

**Resolution:** on a new account run `terraform init -reconfigure`. Never `-migrate-state` across accounts; old state references resources that no longer exist.

### T-6 — Bucket already exists / wrong account errors

Bucket names are globally unique and embed the account ID. When changing accounts, update `bootstrap/main.tf`, `backend.tf`, and the ECR repositories in `helm/shoplite/values.yaml`, then `terraform init -reconfigure`.

---

## 11. Deployment Pre-Flight Checklist

Before starting a deployment cycle, confirm:

- [ ] `aws sts get-caller-identity` returns the expected account; account-specific identifiers updated if it changed (T-6)
- [ ] WSL toolchain present: ansible, boto3, session-manager-plugin (Section 6.1); `~/.aws` synced
- [ ] State backend exists (or bootstrap applied); root `terraform init -reconfigure` succeeds
- [ ] `terraform apply` completes; instances running with status checks passed
- [ ] SSM heartbeat and execution channel both validated (Section 5) — resolve T-2 before continuing on a restricted account
- [ ] Ansible connectivity check passes (Section 6.3)
- [ ] Cluster bootstrap completes; all nodes `Ready`
- [ ] Images pushed; Helm/GitOps sync healthy; ALB end-to-end checks pass (Section 7.3)
- [ ] Teardown executed and zero-billable-resource checks all return `0` (Section 8)

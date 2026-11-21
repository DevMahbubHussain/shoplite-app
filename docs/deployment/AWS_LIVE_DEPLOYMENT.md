# ShopLite — AWS Live Deployment Runbook

**Scope:** Full process for deploying the ShopLite platform to live AWS infrastructure (EC2 + kubeadm + Helm + GitOps) from a Windows 11/10 workstation with WSL2.

**Reference run:** 2026-11-21, ephemeral demo cycle against a managed sandbox account.

**Outcome of the reference run:**

| Stage | Result |
| :--- | :--- |
| AWS credentials + local tooling | SUCCESS |
| Terraform state backend (S3 + DynamoDB) | SUCCESS |
| Infrastructure (VPC, 3× EC2, ALB, ECR) | SUCCESS |
| SSM agent registration (heartbeat) | SUCCESS |
| SSM execution channels (RunCommand / Sessions) | **BLOCKED** — sandbox org policy suspected |
| Ansible → kubeadm → Helm → GitOps | NOT REACHED (blocked by above) |
| Teardown & cost verification | SUCCESS |

---

## 1. Target Architecture (as provisioned)

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
- Subnets: `10.0.1.0/24`, `10.0.2.0/24` (public — ALB + NAT) · `10.0.10.0/24`, `10.0.20.0/24` (private — K8s nodes)
- Compute: 1 control plane + 2 workers, `t3.medium` (4 GB — kubeadm minimum), Ubuntu 22.04 LTS
- Node IAM role: `AmazonSSMManagedInstanceCore` + `AmazonEC2ContainerRegistryReadOnly`

---

## 2. Prerequisites

### 2.1 Toolchain (verified versions from reference run)

| Tool | Version | Host | Notes |
| :--- | :--- | :--- | :--- |
| AWS CLI | 2.28.16 | Windows | creds in `~/.aws/credentials` |
| Terraform | 1.13.2 | Windows | `-chdir` invocation recommended |
| kubectl | 1.34.1 | Windows | |
| Helm | 4.3.1 | Windows | |
| Docker Desktop | (WSL2 backend) | Windows | image builds + ECR push |
| Ansible | core 2.21.6 | **WSL Ubuntu 24.04** | `~/.local/bin/ansible` |
| amazon.aws collection | (bundled) | WSL | provides `aws_ssm` connection plugin |
| boto3 | 1.44.9 | WSL | required by SSM connection plugin |
| session-manager-plugin | 1.2.896.0 | WSL | `~/.local/bin/session-manager-plugin` |
| WSL | Ubuntu 24.04 (WSL2) | — | Ansible control node |

### 2.2 IAM account requirements

The deploying IAM user must be able to: create/manipulate EC2, ELBv2, S3, DynamoDB, IAM roles/profiles/policies, ECR, SSM (including `ssm:StartSession`), Budgets, and route tables. If the account is an org member (sandbox), verify no SCP denies `ssmmessages.amazonaws.com` actions — see §8 Troubleshooting.

### 2.3 WSL ↔ Windows credential sharing

Ansible's SSM plugin authenticates via boto3, which reads WSL-side `~/.aws`. Either symlink or copy:

```bash
# inside WSL
mkdir -p ~/.aws
cp /mnt/c/Users/<YOU>/.aws/credentials ~/.aws/credentials
cp /mnt/c/Users/<YOU>/.aws/config ~/.aws/config 2>/dev/null
chmod 600 ~/.aws/*
```

Verify: `aws sts get-caller-identity` must return the expected account.

---

## 3. Phase 1 — Terraform State Backend (Bootstrap)

The root backend (`terraform/backend.tf`) points at S3 + DynamoDB. The bucket name embeds the **account ID** — S3 names are global, so every new AWS account needs its own renamed bucket.

**Files to touch when switching accounts (old ID → new ID):**

1. `terraform/bootstrap/main.tf` → `state_bucket_name` default
2. `terraform/backend.tf` → `bucket`
3. `helm/shoplite/values.yaml` → 3× ECR `repository:` fields (`<account>.dkr.ecr.<region>.amazonaws.com/...`)

**Commands:**

```bash
cd terraform/bootstrap
terraform init
terraform apply -auto-approve
# → creates S3 bucket (versioned, SSE-S3, public-access blocked) + DynamoDB lock table

cd ..          # terraform/
terraform init -reconfigure
# -reconfigure = fresh remote state; do NOT -migrate-state across accounts
```

**Reference-run outputs:** bucket `shoplite-tfstate-904907793701`, table `shoplite-tflocks`.

**Gate:** `terraform init` succeeds against the remote backend.

---

## 4. Phase 2 — Infrastructure Apply

```bash
terraform -chdir=<repo>/terraform plan  -no-color -input=false   # review
terraform -chdir=<repo>/terraform apply -auto-approve -no-color -input=false
```

Apply takes **5–10 minutes** (NAT Gateway + ALB are the slow items).

**Reference-run outputs (artifact values):**

| Output | Value |
| :--- | :--- |
| VPC | `vpc-010dfd8f80fc63760` |
| Control plane | `i-0428f398a5508c587` @ `10.0.10.5` |
| Worker 1 | `i-090c9fe3973ffa5ff` @ `10.0.10.157` |
| Worker 2 | `i-068002d9a8b4ffd01` @ `10.0.20.225` |
| NAT EIP | `13.250.174.46` |
| ALB DNS | `shoplite-prod-alb-1654679591.ap-southeast-1.elb.amazonaws.com` |
| ECR URLs | `904907793701.dkr.ecr.ap-southeast-1.amazonaws.com/shoplite-{web,catalog-api,order-worker}` |
| SSM profile | `shoplite-prod-node-profile` |

**Gates:** apply exits 0 · ALB DNS resolves · all 3 instances `running` with status checks `passed`:

```bash
aws ec2 describe-instance-status --instance-ids <cp-id> \
  --query "InstanceStatuses[].{state:InstanceState.Name,sys:InstanceStatus.Status}"
```

---

## 5. Phase 3 — Zero-Port Access Validation (SSM)

Nodes have **no public IPs and no SSH keys**; all administration is via SSM. Wait ~2–3 minutes post-boot for agent registration, then:

```bash
aws ssm describe-instance-information \
  --query "InstanceInformationList[].{id:InstanceId,ping:PingStatus,agent:AgentVersion}"
# expect: PingStatus = Online for all 3
```

Also validate **freshness** — compare `LastPingDateTime` against current time; a stale timestamp with `Online` status means cached data (see §8.1).

**Execution channel probe:**

```bash
CMD_ID=$(aws ssm send-command --instance-ids <cp-id> \
  --document-name AWS-RunShellScript \
  --parameters commands="hostname && uptime" \
  --query "Command.CommandId" --output text)
sleep 12
aws ssm list-command-invocations --command-id "$CMD_ID" --details \
  --query "CommandInvocations[].{status:Status,output:CommandPlugins[0].Output}"
# expect: Success + hostname output
```

**Reference-run finding:** heartbeat (`ssm.*`) healthy, but BOTH execution channels (RunCommand delivery via `ssmmessages.*` and Session Manager) failed — `TargetNotConnected` on StartSession, commands stuck `Pending` — across all 3 nodes, persisting across reboots. See §8.2.

---

## 6. Phase 4 — Ansible over SSM (Cluster Bootstrap)

### 6.1 One-time WSL tooling (sudo-free install chain)

Ubuntu 24.04 ships no `pip`; apt installs need an interactive sudo password, which breaks unattended runs. The reproducible sudo-free chain:

```bash
# inside WSL — all steps idempotent
curl -sS https://bootstrap.pypa.io/get-pip.py -o ~/get-pip.py
python3 ~/get-pip.py --user --break-system-packages      # PEP 668 override required
~/.local/bin/pip install --user --break-system-packages ansible boto3

# Session Manager plugin (binary extracted from .deb, no dpkg install needed)
curl -sS -o ~/smp.deb \
  https://s3.amazonaws.com/session-manager-downloads/plugin/latest/ubuntu_64bit/session-manager-plugin.deb
dpkg-deb -x ~/smp.deb ~/smp-extract
cp ~/smp-extract/usr/local/sessionmanagerplugin/bin/session-manager-plugin ~/.local/bin/
chmod +x ~/.local/bin/session-manager-plugin
rm -rf ~/smp.deb ~/smp-extract
```

> **WSL gotcha:** `/tmp` is wiped whenever the WSL VM idles out. Every multi-step command touching `/tmp` must run as a single chained invocation, or use `~/` paths.

Verify: `~/.local/bin/ansible --version` · `~/.local/bin/session-manager-plugin --version` · `ansible-doc -t connection -l | grep ssm`

### 6.2 Inventory anatomy (`ansible/inventory/hosts.yml`)

Each node carries its `instance_id` (from `terraform output`); group vars wire the SSM transport:

```yaml
k8s_cluster:
  vars:
    ansible_connection: amazon.aws.aws_ssm
    ansible_aws_ssm_instance_id: <per-host>
    ansible_aws_ssm_region: ap-southeast-1
    ansible_aws_ssm_bucket_name: <artifacts-bucket>     # module file transfer
    ansible_aws_ssm_plugin: /home/<you>/.local/bin/session-manager-plugin
```

Create the artifacts bucket once:

```bash
aws s3api create-bucket --bucket shoplite-ansible-artifacts-<account> \
  --region ap-southeast-1 \
  --create-bucket-configuration LocationConstraint=ap-southeast-1
aws s3api put-public-access-block --bucket shoplite-ansible-artifacts-<account> \
  --public-access-block-configuration "BlockPublicAcls=true,IgnorePublicAcls=true,BlockPublicPolicy=true,RestrictPublicBuckets=true"
```

> **WSL gotcha:** NTFS-mounted repos (`/mnt/e/...`) are world-writable, so Ansible **ignores `ansible.cfg`** found there. Always pass the inventory explicitly: `-i inventory/hosts.yml`.

### 6.3 Execution sequence

```bash
cd /mnt/<repo>/ansible   # inside WSL

# Gate 1 — transport connectivity
~/.local/bin/ansible k8s_cluster -i inventory/hosts.yml -m ping

# Gate 2 — OS hardening (deploy/ops users, sshd lockdown, /var/log/shoplite ACLs, UFW, backup timer)
~/.local/bin/ansible-playbook -i inventory/hosts.yml playbooks/harden.yml

# Gate 3 — containerd runtime
~/.local/bin/ansible-playbook -i inventory/hosts.yml playbooks/containerd.yml

# Gate 4 — kubeadm cluster (kubelet/kubeadm/kubectl v1.29, init with Calico v3.27, join workers)
~/.local/bin/ansible-playbook -i inventory/hosts.yml playbooks/k8s-cluster.yml

# Gate 5 — kubeconfig retrieval
~/.local/bin/ansible-playbook -i inventory/hosts.yml playbooks/fetch-kubeconfig.yml
export KUBECONFIG=/mnt/<repo>/ansible/kubeconfig
kubectl get nodes -o wide        # expect 1 control-plane + 2 workers = Ready
```

Expected per-node runtime: harden ~2–3 min, containerd ~2 min, k8s-cluster ~6–8 min (kubeadm init + Calico).

---

## 7. Phases 5–7 — Images, Helm, GitOps, Verification

*(designed sequence; blocked in reference run before this point)*

### 7.1 Push images to ECR

```bash
AWS_ACCOUNT=<account>; REGION=ap-southeast-1
aws ecr get-login-password --region $REGION | \
  docker login --username AWS --password-stdin $AWS_ACCOUNT.dkr.ecr.$REGION.amazonaws.com

for svc in web catalog-api order-worker; do
  docker build -t $AWS_ACCOUNT.dkr.ecr.$REGION.amazonaws.com/shoplite-$svc:latest \
    --build-arg TARGET=prod services/$svc
  docker push $AWS_ACCOUNT.dkr.ecr.$REGION.amazonaws.com/shoplite-$svc:latest
done
```

### 7.2 Helm + ArgoCD

```bash
# API server is worker-SG-only (6443); tunnel it through SSM port-forward
aws ssm start-session --target <cp-id> \
  --document-name AWS-StartPortForwardingSessionToRemoteHost \
  --parameters '{"host":["10.0.10.5"],"portNumber":["6443"],"localPortNumber":["6443"]}'

helm upgrade --install shoplite helm/shoplite -n shoplite --create-namespace \
  -f helm/shoplite/values.yaml
# or via GitOps:
kubectl apply -n argocd -f https://raw.githubusercontent.com/argoproj/argo-cd/stable/manifests/install.yaml
kubectl apply -f <shoplite-gitops>/argocd/apps/shoplite-dev-app.yaml
kubectl get pods,svc,ingress,hpa,pdb -n shoplite
```

### 7.3 End-to-end verification through ALB

```bash
ALB=shoplite-prod-alb-<id>.ap-southeast-1.elb.amazonaws.com
curl -s http://$ALB/                        # web UI
curl -s http://$ALB/api/products            # ≥ 10 seeded products
curl -s -X POST http://$ALB/api/orders \
     -H "Content-Type: application/json" \
     -d '{"product_id":1,"quantity":2}'     # 201 Created, status PENDING
# poll GET /api/orders/{id} → PROCESSING → COMPLETED
curl -s http://$ALB/api/metrics | grep orders_
```

---

## 8. Troubleshooting Appendix (reference-run incident log)

### 8.1 Stale SSM "Online" status

**Symptom:** `describe-instance-information` shows `Online`, but `LastPingDateTime` is an hour old; commands hang `Pending`.
**Cause:** SSM caches registration state; heartbeat can silently stop while the registry entry persists.
**Fix:** compare ping timestamps with wall clock (`date`) before trusting `Online`. Recover agents with `aws ec2 reboot-instances` (reboot took effect within ~2 minutes in the reference run).

### 8.2 Execution channels dead while heartbeat alive (reference-run blocker)

**Symptoms (all 3 nodes):**
- `ssm send-command` → accepted, stays `Pending` forever
- `aws ssm start-session` → `TargetNotConnected: <id> is not connected`
- Heartbeat pings fresh; EC2 status checks `passed`; console log clean; SSM Agent v3.3.4793.0 started normally

**Diagnostics performed:**
1. Node IAM role intact — exactly `AmazonSSMManagedInstanceCore` + ECR read, no inline policies, no permissions boundary → IAM *not* the cause
2. `https://ssmmessages.ap-southeast-1.amazonaws.com` reachable globally (TLS OK) → service up
3. Reboots restored heartbeats but **not** execution channels → persistent condition, not a crash loop
4. Account is an org member (`o-h7l8nbgzuh`, ALL features) → **org Service Control Policy restricting `ssmmessages:*` for instance roles is the leading suspect** (heartbeat uses `ssm.*`; both dead channels use `ssmmessages.*`)

**Resolution paths (if encountered again):**
1. Confirm via `aws organizations describe-effective-policy --policy-type SERVICE_CONTROL_POLICY --target-id <account>` (must be called in `us-east-1`) — or ask the sandbox provider
2. If SCP-confirmed: SSM administration is impossible for nodes → use a **temporary bastion** (small EC2 in a public subnet + key pair + SG rule allowing port 22 from bastion SG only), run Ansible over SSH ProxyJump, then destroy the bastion after bootstrap. This is break-glass only — it must not survive teardown.
3. On a normal (non-org-restricted) account, none of this section applies.

### 8.3 Ansible config ignored from `/mnt/*` (world-writable)

**Symptom:** `Could not match supplied host pattern` / inventory silently empty.
**Cause:** Ansible refuses auto-loading `ansible.cfg` from world-writable dirs (all NTFS mounts are 0777).
**Fix:** always pass `-i inventory/hosts.yml` explicitly.

### 8.4 pip refuses to install in WSL (PEP 668)

**Fix:** `get-pip.py --user --break-system-packages`, then `pip install --user --break-system-packages ...`.

### 8.5 Terraform init prompts to migrate state after backend switch

**Fix:** fresh account ⇒ `terraform init -reconfigure` (never `-migrate-state` across accounts; stale state references destroyed resources).

### 8.6 Old account ID baked into config

S3 names are globally unique. When changing accounts, update: `bootstrap/main.tf` bucket default, `backend.tf` bucket, and the 3 ECR repositories in `helm/shoplite/values.yaml` (grep for the old numeric ID to catch strays).

---

## 9. Teardown (mandatory for ephemeral runs)

```bash
# 1. Destroy root stack (VPC, EC2, ALB, ECR, NAT, budgets) — ~5–10 min
terraform -chdir=<repo>/terraform destroy -auto-approve -no-color -input=false

# 2. Empty + destroy the state backend
aws s3api delete-objects --bucket shoplite-tfstate-<account> \
  --delete "$(aws s3api list-object-versions --bucket shoplite-tfstate-<account> \
  --query '{Objects: Versions[].{Key:Key,VersionId:VersionId}}')"
cd terraform/bootstrap && terraform destroy -auto-approve && cd ../..

# 3. Remove the Ansible artifacts bucket
aws s3api delete-objects --bucket shoplite-ansible-artifacts-<account> \
  --delete "$(aws s3api list-object-versions --bucket shoplite-ansible-artifacts-<account> \
  --query '{Objects: Versions[].{Key:Key,VersionId:VersionId}}')"
aws s3 rb s3://shoplite-ansible-artifacts-<account> --region ap-southeast-1

# 4. Verify zero billable resources
aws ec2 describe-instances    --filters Name=instance-state-name,Values=running --query "length(Reservations)"
aws ec2 describe-nat-gateways --filter Name=state,Values=available        --query "length(NatGateways)"
aws elbv2 describe-load-balancers --query "length(LoadBalancers)"
aws s3 ls                                   # only expected buckets remain
aws ecr describe-repositories --query "length(repositories)"
```

**Gate:** every count = `0`.

---

## 10. Cost Model (ap-southeast-1, on-demand)

| Resource | Rate | Daily |
| :--- | :--- | :--- |
| 3× t3.medium | ~$0.0416/hr each | ~$3.00 |
| NAT Gateway | ~$0.045/hr + data | ~$1.10 |
| ALB | ~$0.0225/hr + LCU | ~$0.60 |
| EBS 3× 30 GB gp3 | ~$0.08/GB-mo | ~$0.25 |
| **Total (idle cluster)** | | **~$5/day** |

An ephemeral demo day costs <$10. Leaving the stack up costs ~$80–120/month — always tear down (§9).

---

## 11. Fast Re-Run Checklist (next live attempt)

1. `aws sts get-caller-identity` → confirm account; update account-ID references if changed (§8.6)
2. WSL: verify ansible + session-manager-plugin still installed (§6.1); `~/.aws` creds synced
3. `terraform/bootstrap` apply (skip if bucket+table already exist) → root `terraform init -reconfigure`
4. Root `terraform apply` (~8 min)
5. SSM heartbeat + **execution-channel probe** (§5) — **stop here if channels fail** (§8.2)
6. Ansible gates 1–5 (§6.3)
7. ECR push → Helm/ArgoCD → ALB verification (§7)
8. Teardown (§9) + cost verification

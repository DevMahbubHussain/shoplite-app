# 5. AWS Infrastructure as Code & Ansible (Question 4)

This section details how to validate Terraform modules, simulate infrastructure plans, verify S3 remote state locking, and test Ansible playbooks.

---

## 5.1 Terraform Modular Architecture

The Terraform codebase resides in `terraform/`:

```
terraform/
├── main.tf                 # Provider setup & module orchestrator
├── variables.tf            # Global input variables
├── outputs.tf              # ALB DNS, VPC ID, ECR repository URLs
├── versions.tf             # AWS Provider (~> 5.0) & Terraform constraints
├── backend.tf              # Remote S3 state backend + DynamoDB lock
├── terraform.tfvars        # Active deployment values
└── modules/
    ├── network/            # VPC across 2 AZs (2 Public, 2 Private Subnets, IGW, NAT)
    ├── compute/            # 1 Control Plane, 2 Worker EC2s in Private Subnets (SSM IAM)
    ├── alb/                # Public ALB, HTTP Listener, NodePort Target Groups
    └── ecr/                # 3 ECR Repositories (web, catalog-api, order-worker)
```

---

## 5.2 Validating Terraform Syntax & Configuration

From the repository root:

```bash
cd terraform

# 1. Format check
terraform fmt -check

# 2. Local backend initialization (for syntax and module inspection)
terraform init -backend=false

# 3. Validate configuration
terraform validate
```

### Expected Output:
```text
Success! The configuration is valid.
```

---

## 5.3 Simulating Infrastructure Plan

To generate a full execution plan against AWS:

```bash
# Export your AWS credentials
export AWS_REGION="us-east-1"
export AWS_ACCESS_KEY_ID="<YOUR_KEY>"
export AWS_SECRET_ACCESS_KEY="<YOUR_SECRET>"

# Initialize with remote S3 backend
terraform init

# Generate execution plan
terraform plan -out=tfplan
```

### Key Resources Verified in Plan:
1. `module.network.aws_vpc.main`: CIDR `10.0.0.0/16`.
2. `module.network.aws_subnet.public[*]`: `10.0.1.0/24`, `10.0.2.0/24` (Hosts ALB & NAT).
3. `module.network.aws_subnet.private[*]`: `10.0.10.0/24`, `10.0.20.0/24` (Hosts K8s nodes).
4. `module.compute.aws_instance.control_plane` & `workers[*]`: In private subnets with `AmazonSSMManagedInstanceCore` IAM policy. Zero SSH port 22 open to the public internet.
5. `module.alb.aws_lb.public`: Public internet-facing ALB.
6. `module.ecr.aws_ecr_repository.*`: ECR registries with image scanning on push enabled.
7. `aws_budgets_budget.cost_guard`: $20 budget limit alarm.

::: caution Cost Guard & Teardown Protocol
Always execute `terraform destroy` after grading or evaluation is complete to tear down all billable AWS resources (NAT Gateway, ALB, EC2 instances).
:::

---

## 5.4 Ansible Playbook Syntax & Dry-Run Check

The Ansible playbooks in `ansible/` configure the operating system and provision the cluster:

```bash
cd ansible

# 1. Verify syntax across all playbooks
ansible-playbook --syntax-check playbooks/harden.yml
ansible-playbook --syntax-check playbooks/containerd.yml
ansible-playbook --syntax-check playbooks/k8s-cluster.yml
ansible-playbook --syntax-check playbooks/fetch-kubeconfig.yml

# 2. Execute dry-run / check mode (when inventory is populated)
ansible-playbook -i inventory/hosts.yml playbooks/harden.yml --check
```

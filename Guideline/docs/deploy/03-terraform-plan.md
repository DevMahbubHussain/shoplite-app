# Phase 3: Terraform Plan (Read-Only Cloud Validation)

## What

A full `terraform plan` against AWS — proving the four infrastructure modules (`network`, `compute`, `alb`, `ecr`) produce a valid 37-resource execution plan — **without creating or costing anything**.

## Why

`plan` exercises the entire configuration: provider auth, module wiring, data sources (AMI lookup), and IAM assumptions — all API reads, zero writes. It is the strongest no-cost evidence that the infrastructure code is cloud-valid. A previous full apply cycle (documented in `docs/deployment/AWS_LIVE_DEPLOYMENT.md`) provisioned this exact topology for real.

## How

The declared backend is S3+DynamoDB. To plan without a live state bucket, override the backend locally for the run:

```hcl
# terraform/backend_override.tf  (temporary, not committed)
terraform {
  backend "local" {}
}
```

```bash
terraform -chdir=terraform init -reconfigure -no-color
terraform -chdir=terraform plan -no-color -input=false
```

## Topology produced by the plan (37 resources)

| Module | Resources |
| :--- | :--- |
| `network` | VPC (DNS on), 2 public + 2 private subnets across 2 AZs, IGW, NAT Gateway + EIP, route tables + associations |
| `compute` | 1 control plane + 2 worker `t3.medium` (Ubuntu 22.04, private subnets, EBS-encrypted), SSM + ECR-read IAM role/profile, node security groups |
| `alb` | Public ALB (2 AZ), listeners, target groups on worker NodePorts |
| `ecr` | 3 repositories: `shoplite-web`, `shoplite-catalog-api`, `shoplite-order-worker` |

Plus the budget alarm resource with the `$20` monthly limit.

## Evidence

<img src="/screenshots/Q4-aws-iac/D1-terraform-plan.png" alt="Terraform plan resources" width="440">
<img src="/screenshots/Q4-aws-iac/D2-plan-summary.png" alt="Plan summary" width="440">

Full plan text: `docs/evidence/terraform-plan-2026-11-21.txt` — ends with:

```
Plan: 37 to add, 0 to change, 0 to destroy.
```

## Gate

Plan exits clean with exactly the expected resource set and zero destructive actions.

Next: [Phase 4 — Kind Kubernetes Cluster](/deploy/04-kind-cluster).

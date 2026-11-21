# Phase 8: Teardown & Cost Discipline

## What

The controlled removal of every deployed component — local cluster, port-forwards, and (for cloud runs) the full Terraform stack — leaving zero billable or lingering resources.

## Why

A deployment that cannot be cleanly removed is not production-grade. Teardown discipline keeps workstations and cloud accounts reproducible, and for cloud runs it is the difference between a $5 demo day and an $80–120/month surprise.

## How

### Local components

```bash
# Stop port-forwards (Ctrl+C or:)
taskkill //F //IM kubectl.exe        # Windows note: closes all kubectl ports

# Delete the kind cluster (removes node container, images stay in Docker)
kind delete cluster --name shoplite

# Stop the Compose stack (containers + network; volumes preserved unless -v)
docker compose down
```

### Cloud run (when a real apply was executed)

```bash
terraform -chdir=terraform destroy -auto-approve -no-color -input=false

# State backend (bucket is lifecycle-protected; empty it via CLI first)
aws s3api delete-objects --bucket shoplite-tfstate-<account> \
  --delete "$(aws s3api list-object-versions --bucket shoplite-tfstate-<account> \
  --query '{Objects: Versions[].{Key:Key,VersionId:VersionId}}')"
aws s3 rb s3://shoplite-tfstate-<account> --region ap-southeast-1
aws dynamodb delete-table --table-name shoplite-tflocks --region ap-southeast-1

# Ansible artifacts bucket
aws s3 rb s3://shoplite-ansible-artifacts-<account> --force --region ap-southeast-1

# Zero-billable verification — every count must be 0
aws ec2 describe-instances --filters Name=instance-state-name,Values=running --query "length(Reservations)"
aws ec2 describe-nat-gateways --filter Name=state,Values=available --query "length(NatGateways)"
aws elbv2 describe-load-balancers --query "length(LoadBalancers)"
aws ecr describe-repositories --query "length(repositories)"
aws s3 ls; aws dynamodb list-tables --region ap-southeast-1
aws iam list-roles --query "Roles[?contains(RoleName,'shoplite')].RoleName"
```

Full teardown protocol with the SSM incident log: `docs/deployment/AWS_LIVE_DEPLOYMENT.md`.

## Cost model (ap-southeast-1, on-demand)

| Resource | Rate | Daily |
| :--- | :--- | :--- |
| 3× t3.medium | ~$0.0416/hr each | ~$3.00 |
| NAT Gateway | ~$0.045/hr + data | ~$1.10 |
| ALB | ~$0.0225/hr + LCU | ~$0.60 |
| EBS 3× 30 GB gp3 | ~$0.08/GB-mo | ~$0.25 |
| **Idle cluster total** | | **~$5/day** |

The 2026-11-21 cloud run was torn down the same day with all seven zero-count checks passing — the account accrued no further charges.

## Gate

Local: `kind get clusters` returns nothing; `docker compose ps` is empty.
Cloud: all verification counts return `0`.

Back to the [walkthrough overview](/deploy/).

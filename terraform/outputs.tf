# Root Output Exports for ShopLite AWS Infrastructure

output "vpc_id" {
  value       = module.network.vpc_id
  description = "The ID of the provisioned custom VPC"
}

output "public_subnet_ids" {
  value       = module.network.public_subnet_ids
  description = "IDs of the public subnets across 2 Availability Zones"
}

output "private_subnet_ids" {
  value       = module.network.private_subnet_ids
  description = "IDs of the private subnets across 2 Availability Zones"
}

output "nat_gateway_ip" {
  value       = module.network.nat_gateway_ip
  description = "Public Elastic IP address of the NAT Gateway"
}

output "alb_dns_name" {
  value       = module.alb.alb_dns_name
  description = "Publicly accessible DNS hostname of the Application Load Balancer"
}

output "alb_arn" {
  value       = module.alb.alb_arn
  description = "ARN of the Application Load Balancer"
}

output "control_plane_private_ip" {
  value       = module.compute.control_plane_private_ip
  description = "Private IP address of the Kubernetes control plane EC2 instance"
}

output "worker_private_ips" {
  value       = module.compute.worker_private_ips
  description = "Private IP addresses of the Kubernetes worker EC2 instances"
}

output "ssm_instance_profile_name" {
  value       = module.compute.ssm_instance_profile_name
  description = "IAM instance profile name attached to all cluster nodes for SSM management"
}

output "ecr_repository_urls" {
  value       = module.ecr.repository_urls
  description = "Map of ECR repository URLs for shoplite container images"
}

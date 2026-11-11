# Root Input Variables for ShopLite AWS Infrastructure

variable "aws_region" {
  type        = string
  default     = "ap-southeast-1"
  description = "AWS deployment region"
}

variable "environment" {
  type        = string
  default     = "prod"
  description = "Deployment environment name (e.g. dev, prod)"
}

variable "project_name" {
  type        = string
  default     = "shoplite"
  description = "Base project identifier used for naming and resource tagging"
}

variable "vpc_cidr" {
  type        = string
  default     = "10.0.0.0/16"
  description = "Primary CIDR block for the custom VPC"
}

variable "availability_zones" {
  type        = list(string)
  default     = ["ap-southeast-1a", "ap-southeast-1b"]
  description = "Target Availability Zones for multi-AZ high availability"
}

variable "public_subnet_cidrs" {
  type        = list(string)
  default     = ["10.0.1.0/24", "10.0.2.0/24"]
  description = "CIDR allocations for public subnets hosting ALB and NAT Gateway"
}

variable "private_subnet_cidrs" {
  type        = list(string)
  default     = ["10.0.10.0/24", "10.0.20.0/24"]
  description = "CIDR allocations for private subnets hosting Kubernetes compute nodes"
}

variable "instance_type" {
  type        = string
  default     = "t3.medium"
  description = "EC2 instance type for Kubernetes control plane and worker nodes"
}

variable "worker_count" {
  type        = number
  default     = 2
  description = "Number of Kubernetes worker instances to launch in private subnets"
}

variable "budget_limit_usd" {
  type        = string
  default     = "20.0"
  description = "Monthly cost budget limit in USD"
}

variable "budget_alert_email" {
  type        = string
  default     = "sre-alerts@shoplite.internal"
  description = "Recipient email address for AWS Budget cost alarms"
}

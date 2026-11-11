# ALB Module Input Variables

variable "project_name" {
  type        = string
  description = "Project identifier"
}

variable "environment" {
  type        = string
  description = "Deployment environment"
}

variable "vpc_id" {
  type        = string
  description = "VPC ID where the ALB and Target Group reside"
}

variable "public_subnet_ids" {
  type        = list(string)
  description = "Public subnet IDs spanning across at least 2 Availability Zones"
}

variable "target_instances" {
  type        = list(string)
  description = "List of worker EC2 instance IDs to register with the Target Group"
}

variable "nodeport_http" {
  type        = number
  default     = 30080
  description = "Target NodePort where Ingress Controller / Nginx routes external HTTP traffic"
}

# Compute Module Input Variables

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
  description = "VPC ID where instances and security groups reside"
}

variable "private_subnet_ids" {
  type        = list(string)
  description = "Private subnet IDs where instances are deployed"
}

variable "instance_type" {
  type        = string
  default     = "t3.medium"
  description = "EC2 instance type for nodes"
}

variable "worker_count" {
  type        = number
  default     = 2
  description = "Number of worker nodes to launch"
}

variable "alb_security_group_id" {
  type        = string
  description = "Security group ID of the Application Load Balancer to permit NodePort ingress"
}

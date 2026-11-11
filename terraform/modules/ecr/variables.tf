# ECR Module Input Variables

variable "project_name" {
  type        = string
  description = "Project identifier"
}

variable "environment" {
  type        = string
  description = "Deployment environment"
}

variable "repository_names" {
  type        = list(string)
  default     = ["shoplite-web", "shoplite-catalog-api", "shoplite-order-worker"]
  description = "List of container image repositories to create"
}

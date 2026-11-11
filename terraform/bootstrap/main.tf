# S3 Bucket and DynamoDB Lock Table for Terraform Remote State Backend

provider "aws" {
  region = var.aws_region

  default_tags {
    tags = {
      project     = "shoplite"
      environment = "bootstrap"
      managed_by  = "terraform"
    }
  }
}

variable "aws_region" {
  type        = string
  default     = "ap-southeast-1"
  description = "AWS deployment region"
}

variable "state_bucket_name" {
  type        = string
  default     = "shoplite-tfstate-263303066497"
  description = "Name of the S3 bucket for Terraform remote state"
}

variable "lock_table_name" {
  type        = string
  default     = "shoplite-tflocks"
  description = "Name of the DynamoDB table for Terraform state locking"
}

# 1. Remote State S3 Bucket
resource "aws_s3_bucket" "tf_state" {
  bucket        = var.state_bucket_name
  force_destroy = false

  lifecycle {
    prevent_destroy = true
  }
}

# Enforce Versioning
resource "aws_s3_bucket_versioning" "tf_state_versioning" {
  bucket = aws_s3_bucket.tf_state.id
  versioning_configuration {
    status = "Enabled"
  }
}

# Enforce Server-Side Encryption (SSE-S3)
resource "aws_s3_bucket_server_side_encryption_configuration" "tf_state_crypto" {
  bucket = aws_s3_bucket.tf_state.id

  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm = "AES256"
    }
  }
}

# Block all public ingress to the state bucket
resource "aws_s3_bucket_public_access_block" "tf_state_public_block" {
  bucket = aws_s3_bucket.tf_state.id

  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

# 2. DynamoDB State Locking Table
resource "aws_dynamodb_table" "tf_locks" {
  name         = var.lock_table_name
  billing_mode = "PAY_PER_REQUEST"
  hash_key     = "LockID"

  attribute {
    name = "LockID"
    type = "S"
  }

  point_in_time_recovery {
    enabled = true
  }
}

output "state_bucket_arn" {
  value       = aws_s3_bucket.tf_state.arn
  description = "ARN of the S3 state bucket"
}

output "dynamodb_table_name" {
  value       = aws_dynamodb_table.tf_locks.name
  description = "Name of the DynamoDB lock table"
}

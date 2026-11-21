# Terraform Remote State Configuration
# Stores execution state remotely in an S3 bucket with state locking via DynamoDB

terraform {
  backend "s3" {
    bucket         = "shoplite-tfstate-904907793701"
    key            = "infrastructure/terraform.tfstate"
    region         = "ap-southeast-1"
    dynamodb_table = "shoplite-tflocks"
    encrypt        = true
  }
}

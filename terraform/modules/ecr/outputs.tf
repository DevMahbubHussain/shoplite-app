# ECR Module Outputs

output "repository_urls" {
  value = {
    for idx, repo in aws_ecr_repository.repos :
    var.repository_names[idx] => repo.repository_url
  }
  description = "Map of repository names to their corresponding ECR clone URLs"
}

output "repository_arns" {
  value       = aws_ecr_repository.repos[*].arn
  description = "List of ECR repository ARNs"
}

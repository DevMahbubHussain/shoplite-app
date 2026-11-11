# Compute Module Outputs

output "control_plane_instance_id" {
  value       = aws_instance.control_plane.id
  description = "Instance ID of the control plane node"
}

output "control_plane_private_ip" {
  value       = aws_instance.control_plane.private_ip
  description = "Private IP of the control plane node"
}

output "worker_instance_ids" {
  value       = aws_instance.workers[*].id
  description = "List of worker node instance IDs"
}

output "worker_private_ips" {
  value       = aws_instance.workers[*].private_ip
  description = "List of worker node private IP addresses"
}

output "worker_security_group_id" {
  value       = aws_security_group.worker.id
  description = "Security group ID for worker nodes"
}

output "ssm_instance_profile_name" {
  value       = aws_iam_instance_profile.node_profile.name
  description = "IAM instance profile name attached to compute nodes"
}

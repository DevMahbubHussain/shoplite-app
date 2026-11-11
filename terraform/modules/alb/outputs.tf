# ALB Module Outputs

output "alb_id" {
  value       = aws_lb.main.id
  description = "The ID of the Application Load Balancer"
}

output "alb_arn" {
  value       = aws_lb.main.arn
  description = "The ARN of the Application Load Balancer"
}

output "alb_dns_name" {
  value       = aws_lb.main.dns_name
  description = "Public DNS hostname of the Application Load Balancer"
}

output "alb_zone_id" {
  value       = aws_lb.main.zone_id
  description = "Canonical hosted zone ID of the ALB (for Route 53 aliases)"
}

output "alb_security_group_id" {
  value       = aws_security_group.alb.id
  description = "Security group ID of the ALB"
}

output "target_group_arn" {
  value       = aws_lb_target_group.http.arn
  description = "ARN of the HTTP target group"
}

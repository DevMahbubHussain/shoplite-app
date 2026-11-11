# ALB Module: Public Application Load Balancer, Target Groups, and Listeners

# 1. ALB Security Group (Public Ingress 80/443; Egress strictly to K8s NodePort range)
resource "aws_security_group" "alb" {
  name        = "${var.project_name}-${var.environment}-alb-sg"
  description = "Security group for the public Application Load Balancer"
  vpc_id      = var.vpc_id

  ingress {
    description = "HTTP public ingress"
    from_port   = 80
    to_port     = 80
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  ingress {
    description = "HTTPS public ingress"
    from_port   = 443
    to_port     = 443
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  egress {
    description = "Egress to Kubernetes worker NodePort range"
    from_port   = 30000
    to_port     = 32767
    protocol    = "tcp"
    cidr_blocks = ["10.0.0.0/16"]
  }

  tags = {
    Name = "${var.project_name}-${var.environment}-alb-sg"
  }
}

# 2. Public Application Load Balancer
resource "aws_lb" "main" {
  name               = "${var.project_name}-${var.environment}-alb"
  internal           = false
  load_balancer_type = "application"
  security_groups    = [aws_security_group.alb.id]
  subnets            = var.public_subnet_ids

  enable_deletion_protection = false

  tags = {
    Name = "${var.project_name}-${var.environment}-alb"
  }
}

# 3. Target Group (Forwarding to Kubernetes Ingress NodePort 30080)
resource "aws_lb_target_group" "http" {
  name        = "${var.project_name}-${var.environment}-tg-http"
  port        = var.nodeport_http
  protocol    = "HTTP"
  vpc_id      = var.vpc_id
  target_type = "instance"

  health_check {
    enabled             = true
    path                = "/healthz"
    port                = "traffic-port"
    protocol            = "HTTP"
    healthy_threshold   = 3
    unhealthy_threshold = 3
    timeout             = 5
    interval            = 15
    matcher             = "200"
  }

  tags = {
    Name = "${var.project_name}-${var.environment}-tg-http"
  }
}

# 4. Target Group Attachment for Worker Nodes
resource "aws_lb_target_group_attachment" "workers" {
  count            = length(var.target_instances)
  target_group_arn = aws_lb_target_group.http.arn
  target_id        = var.target_instances[count.index]
  port             = var.nodeport_http
}

# 5. HTTP Listener (Port 80 -> Target Group)
resource "aws_lb_listener" "http" {
  load_balancer_arn = aws_lb.main.arn
  port              = 80
  protocol          = "HTTP"

  default_action {
    type             = "forward"
    target_group_arn = aws_lb_target_group.http.arn
  }
}

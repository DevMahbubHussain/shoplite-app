# Compute Module: Control Plane & Worker EC2 Instances, IAM SSM Roles, and Cluster Security Groups

# 1. Fetch Latest Ubuntu 22.04 LTS AMI
data "aws_ami" "ubuntu" {
  most_recent = true
  owners      = ["099720109477"] # Canonical

  filter {
    name   = "name"
    values = ["ubuntu/images/hvm-ssd/ubuntu-jammy-22.04-amd64-server-*"]
  }

  filter {
    name   = "virtualization-type"
    values = ["hvm"]
  }
}

# 2. IAM Role for EC2 Instances (SSM Session Manager & ECR Access)
resource "aws_iam_role" "node_role" {
  name = "${var.project_name}-${var.environment}-node-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = "sts:AssumeRole"
        Effect = "Allow"
        Principal = {
          Service = "ec2.amazonaws.com"
        }
      }
    ]
  })
}

# Attach AmazonSSMManagedInstanceCore for Zero-Port Administrative Access
resource "aws_iam_role_policy_attachment" "ssm_policy" {
  role       = aws_iam_role.node_role.name
  policy_arn = "arn:aws:iam::aws:policy/AmazonSSMManagedInstanceCore"
}

# Attach AmazonEC2ContainerRegistryReadOnly to pull images from ECR
resource "aws_iam_role_policy_attachment" "ecr_policy" {
  role       = aws_iam_role.node_role.name
  policy_arn = "arn:aws:iam::aws:policy/AmazonEC2ContainerRegistryReadOnly"
}

# Instance Profile
resource "aws_iam_instance_profile" "node_profile" {
  name = "${var.project_name}-${var.environment}-node-profile"
  role = aws_iam_role.node_role.name
}

# 3. Security Groups
# Control Plane Security Group
resource "aws_security_group" "control_plane" {
  name        = "${var.project_name}-${var.environment}-control-plane-sg"
  description = "Security group for Kubernetes control plane instance"
  vpc_id      = var.vpc_id

  # Kubernetes API server from worker nodes
  ingress {
    description     = "Kubernetes API server from workers"
    from_port       = 6443
    to_port         = 6443
    protocol        = "tcp"
    security_groups = [aws_security_group.worker.id]
  }

  # etcd server client API
  ingress {
    description = "etcd server client API"
    from_port   = 2379
    to_port     = 2380
    protocol    = "tcp"
    self        = true
  }

  # Kubelet API
  ingress {
    description     = "Kubelet API from workers"
    from_port       = 10250
    to_port         = 10250
    protocol        = "tcp"
    security_groups = [aws_security_group.worker.id]
  }

  # Intra-cluster Calico / Flannel CNI overlay
  ingress {
    description     = "CNI overlay traffic from workers"
    from_port       = 0
    to_port         = 0
    protocol        = "-1"
    security_groups = [aws_security_group.worker.id]
  }

  ingress {
    description = "Self CNI overlay traffic"
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    self        = true
  }

  egress {
    description = "Outbound egress via NAT Gateway"
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = {
    Name = "${var.project_name}-${var.environment}-control-plane-sg"
  }
}

# Worker Nodes Security Group
resource "aws_security_group" "worker" {
  name        = "${var.project_name}-${var.environment}-worker-sg"
  description = "Security group for Kubernetes worker nodes"
  vpc_id      = var.vpc_id

  # Ingress from ALB to Kubernetes NodePort services (30000-32767)
  ingress {
    description     = "NodePort traffic from ALB"
    from_port       = 30000
    to_port         = 32767
    protocol        = "tcp"
    security_groups = [var.alb_security_group_id]
  }

  # Kubelet API from control plane
  ingress {
    description = "Kubelet API intra-worker and control plane"
    from_port   = 10250
    to_port     = 10250
    protocol    = "tcp"
    self        = true
  }

  # Intra-worker CNI overlay communication
  ingress {
    description = "Intra-worker CNI overlay traffic"
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    self        = true
  }

  egress {
    description = "Outbound egress via NAT Gateway"
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = {
    Name = "${var.project_name}-${var.environment}-worker-sg"
  }
}

# Allow control plane to send to worker Kubelet
resource "aws_security_group_rule" "control_plane_to_kubelet" {
  type                     = "ingress"
  from_port                = 10250
  to_port                  = 10250
  protocol                 = "tcp"
  security_group_id        = aws_security_group.worker.id
  source_security_group_id = aws_security_group.control_plane.id
  description              = "Kubelet API from control plane"
}

# 4. EC2 Instances (Residing in Private Subnets with Zero Public IP)
# Control Plane Instance
resource "aws_instance" "control_plane" {
  ami                  = data.aws_ami.ubuntu.id
  instance_type        = var.instance_type
  subnet_id            = var.private_subnet_ids[0]
  iam_instance_profile = aws_iam_instance_profile.node_profile.name

  vpc_security_group_ids = [aws_security_group.control_plane.id]

  root_block_device {
    volume_size           = 30
    volume_type           = "gp3"
    encrypted             = true
    delete_on_termination = true
  }

  user_data = <<-EOF
              #!/bin/bash
              hostnamectl set-hostname shoplite-control-plane
              EOF

  tags = {
    Name = "${var.project_name}-${var.environment}-control-plane"
    Role = "control-plane"
  }
}

# Worker Node Instances
resource "aws_instance" "workers" {
  count                = var.worker_count
  ami                  = data.aws_ami.ubuntu.id
  instance_type        = var.instance_type
  subnet_id            = var.private_subnet_ids[count.index % length(var.private_subnet_ids)]
  iam_instance_profile = aws_iam_instance_profile.node_profile.name

  vpc_security_group_ids = [aws_security_group.worker.id]

  root_block_device {
    volume_size           = 30
    volume_type           = "gp3"
    encrypted             = true
    delete_on_termination = true
  }

  user_data = <<-EOF
              #!/bin/bash
              hostnamectl set-hostname shoplite-worker-${count.index + 1}
              EOF

  tags = {
    Name = "${var.project_name}-${var.environment}-worker-${count.index + 1}"
    Role = "worker"
  }
}

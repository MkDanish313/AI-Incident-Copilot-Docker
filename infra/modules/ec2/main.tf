# Get default VPC
data "aws_vpc" "default" {
  default = true
}

# Get default subnets inside default VPC
data "aws_subnets" "default" {
  filter {
    name   = "vpc-id"
    values = [data.aws_vpc.default.id]
  }
}

# Security Group
resource "aws_security_group" "this" {
  name        = "${var.project_name}-sg"
  description = "Allow SSH, API, Streamlit, Ollama"
  vpc_id      = data.aws_vpc.default.id

  ingress {
    description = "Allow SSH"
    from_port   = 22
    to_port     = 22
    protocol    = "tcp"
    cidr_blocks = [var.my_ip_cidr]
  }

  ingress {
    description = "Allow API"
    from_port   = 8000
    to_port     = 8000
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  ingress {
    description = "Allow Streamlit"
    from_port   = 8501
    to_port     = 8501
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  ingress {
    description = "Allow Ollama (restricted)"
    from_port   = 11434
    to_port     = 11434
    protocol    = "tcp"
    cidr_blocks = [var.my_ip_cidr]
  }

  egress {
    description = "Allow all outbound traffic"
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = {
    Name = "${var.project_name}-sg"
  }
}

# EC2 Instance
resource "aws_instance" "this" {
  ami                         = var.ami_id
  instance_type               = var.instance_type
  subnet_id                   = data.aws_subnets.default.ids[0]
  vpc_security_group_ids      = [aws_security_group.this.id]
  key_name                    = var.key_name
  associate_public_ip_address = true

  user_data = <<-EOF
              #!/bin/bash
              set -eux
              apt-get update -y
              apt-get install -y docker.io docker-compose git
              systemctl enable docker
              systemctl start docker

              # clone & run
              mkdir -p /opt && cd /opt
              if [ ! -d /opt/AI-Incident-Copilot-Docker ]; then
                git clone ${var.repo_url} AI-Incident-Copilot-Docker
              fi
              cd AI-Incident-Copilot-Docker
              mkdir -p data/db data/ollama
              docker-compose up -d --build
              EOF
  
   # Root EBS volume ka size set karne ke liye
  root_block_device {
    volume_size = 25      # Root volume size 25 GB
    volume_type = "gp3"   # gp2 bhi use kar sakte ho
  }

  tags = {
    Name = "${var.project_name}-ec2"
  }
}

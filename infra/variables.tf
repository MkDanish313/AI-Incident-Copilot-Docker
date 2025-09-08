variable "project_name" {
  description = "Project name for tagging resources"
  type        = string
}

variable "region" {
  description = "AWS region to deploy resources"
  type        = string
}

variable "ami_id" {
  description = "Ubuntu 22.04 AMI ID"
  type        = string
}

variable "instance_type" {
  description = "EC2 instance type"
  type        = string
}

variable "key_name" {
  description = "Name of the EC2 key pair"
  type        = string
}

variable "repo_url" {
  description = "GitHub repo to clone"
  type        = string
}

variable "my_ip_cidr" {
  description = "Your IP/CIDR block for SSH access"
  type        = string
}

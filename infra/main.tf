module "ec2" {
  source         = "./modules/ec2"
  project_name   = var.project_name
  ami_id         = var.ami_id
  instance_type  = var.instance_type
  key_name       = var.key_name
  my_ip_cidr     = var.my_ip_cidr
  repo_url       = var.repo_url
}
resource "local_file" "backend_env" {
  content = <<EOT
PUBLIC_API_URL=http://${module.ec2.public_ip}:8000
EOT

  filename = "${path.module}/.env"
}

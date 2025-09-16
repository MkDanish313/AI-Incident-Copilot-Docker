module "ec2" {
  source         = "./modules/ec2"
  project_name   = var.project_name
  ami_id         = var.ami_id
  instance_type  = var.instance_type
  key_name       = var.key_name
  my_ip_cidr     = var.my_ip_cidr
  repo_url       = var.repo_url
}

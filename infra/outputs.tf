output "instance_id" {
  description = "EC2 instance ID from module"
  value       = module.ec2.instance_id
}

output "public_ip" {
  description = "EC2 Public IP from module"
  value       = module.ec2.public_ip
}

output "public_dns" {
  description = "EC2 Public DNS from module"
  value       = module.ec2.public_dns
}

output "urls" {
  description = "Application URLs"
  value = {
    api      = "http://${module.ec2.public_ip}:8000/health"
    frontend = "http://${module.ec2.public_ip}:8501"
  }
}

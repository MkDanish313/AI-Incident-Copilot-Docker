output "public_ip" {
  value = module.ec2.public_ip
}
output "urls" {
  value = {
    api      = "http://${module.ec2.public_ip}:8000/health"
    frontend = "http://${module.ec2.public_ip}:8501"
    ollama   = "http://${module.ec2.public_ip}:11434"
  }
}

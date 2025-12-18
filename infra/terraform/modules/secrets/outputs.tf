output "secret_arn" {
  description = "ARN of the secrets manager secret"
  value       = module.secrets_manager.secret_arn
}

output "secret_id" {
  description = "ID of the secrets manager secret"
  value       = module.secrets_manager.secret_id
}

output "secret_name" {
  description = "Name of the secrets manager secret"
  value       = module.secrets_manager.secret_id
}

output "secret_version_id" {
  description = "Version ID of the secret"
  value       = module.secrets_manager.secret_version_id
}

output "db_password" {
  description = "Generated database password"
  value       = random_password.db_password.result
  sensitive   = true
}

output "db_instance_endpoint" {
  description = "The connection endpoint for the RDS instance"
  value       = module.rds.db_instance_endpoint
}

output "db_instance_address" {
  description = "The address of the RDS instance"
  value       = module.rds.db_instance_address
}

output "db_instance_name" {
  description = "The database name"
  value       = module.rds.db_instance_name
}

output "db_instance_id" {
  description = "The RDS instance ID"
  value       = module.rds.db_instance_identifier
}

output "db_instance_arn" {
  description = "The ARN of the RDS instance"
  value       = module.rds.db_instance_arn
}

output "db_instance_port" {
  description = "The database port"
  value       = module.rds.db_instance_port
}

output "db_subnet_group_name" {
  description = "The db subnet group name"
  value       = aws_db_subnet_group.main.name
}

output "db_subnet_group_id" {
  description = "The db subnet group id"
  value       = aws_db_subnet_group.main.id
}

output "db_parameter_group_name" {
  description = "The db parameter group name"
  value       = aws_db_parameter_group.postgres.name
}

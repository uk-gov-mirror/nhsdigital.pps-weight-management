output "db_endpoint" {
  value = module.rds.db_instance_endpoint
}

output "db_name" {
  value = module.rds.db_instance_name
}
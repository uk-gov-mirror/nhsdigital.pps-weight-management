output "cloudfront_url" {
  value = "https://${aws_cloudfront_distribution.cdn.domain_name}"
}

output "cloudfront_distribution_id" {
  value = aws_cloudfront_distribution.cdn.id
}

output "cognito_issuer" {
  value = "https://cognito-idp.${data.aws_region.current.name}.amazonaws.com/${aws_cognito_user_pool.up.id}"
}

output "cognito_user_pool_id" {
  value = aws_cognito_user_pool.up.id
}

output "cognito_client_id_ci" {
  value = aws_cognito_user_pool_client.ci.id 
}

output "cognito_client_id_spa" {
  value = aws_cognito_user_pool_client.spa.id
}

output "ecr_repository_url" {
  value = aws_ecr_repository.django.repository_url
}

output "ecs_cluster_name" {
  value = aws_ecs_cluster.app.name
}

output "ecs_service_name" {
  value = aws_ecs_service.web.name
}

output "task_definition_web_family" {
  value = aws_ecs_task_definition.django.family
}

output "task_definition_web_arn" {
  value = aws_ecs_task_definition.django.arn
}

output "alb_dns_name" {
  value = aws_lb.app.dns_name
}

# Useful for DB connectivity/migrations (not secret)
output "rds_endpoint" {
  value = aws_db_instance.pg.address
}

# Output the SSM parameter name (safe to expose, not the value)
output "ssm_db_password_param" {
  value = aws_ssm_parameter.db_password.name
}

# EventBridge Scheduler name (optional but handy)
output "scheduler_name" {
  value = aws_scheduler_schedule.daily.name
}

output "bastion_instance_id" {
  description = "Instance ID for SSM port-forward"
  value       = aws_instance.ssm_bastion.id
}
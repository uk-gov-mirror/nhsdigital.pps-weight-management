output "vpc_id" {
  value = module.vpc.vpc_id
}

output "public_subnet_ids" {
  value = module.vpc.public_subnets
}

output "private_subnet_ids" {
  value = module.vpc.private_subnets # [0] for ECS, [1] for RDS
}

output "alb_sg_id" {
  description = "The ID of the Application Load Balancer security group."
  value       = module.security_groups.alb_sg_id
}

output "ecs_sg_id" {
  description = "The ID of the ECS security group."
  value       = module.security_groups.ecs_sg_id
}

output "rds_sg_id" {
  description = "The ID of the RDS security group."
  value       = module.security_groups.rds_sg_id
}
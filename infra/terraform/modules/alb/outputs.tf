output "lb_arn" {
  description = "The ARN of the load balancer"
  value       = module.alb.arn
}

output "lb_dns_name" {
  description = "The DNS name of the load balancer"
  value       = module.alb.dns_name
}

output "target_group_arns" {
  description = "Map of target group ARNs"
  value       = { for k, v in module.alb.target_groups : k => v.arn }
}

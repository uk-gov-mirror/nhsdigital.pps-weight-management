
variable "project" { type = string }
variable "env"     { type = string }
variable "region"  { type = string }

# VPC inputs (safe defaults; override in tfvars if needed)
variable "vpc_cidr" {
  description = "VPC CIDR"
  type        = string
  default     = "10.0.0.0/16"
}

variable "azs" {
  description = "Availability Zones to use"
  type        = list(string)
  default     = ["eu-west-2a", "eu-west-2b"]
}

variable "public_subnet_cidrs" {
  description = "CIDRs for public subnets"
  type        = list(string)
  default     = ["10.0.0.0/20", "10.0.16.0/20"]
}

variable "private_subnet_cidrs" {
  description = "CIDRs for private subnets"
  type        = list(string)
  default     = ["10.0.128.0/20", "10.0.144.0/20"]
}

# Django container
variable "django_image_tag" {
  description = "Tag for the Django image pushed to ECR"
  type        = string
  default     = "latest"
}

variable "django_container_port" {
  description = "Container port Django/Gunicorn listens on"
  type        = number
  default     = 8000
}

# Database
variable "db_name" { 
  type    = string  
  default = "appdb"
}
  
variable "db_username" {
  type    = string
  default = "appuser" 
}

variable "db_allocated_storage" { 
  type    = number  
  default = 20   # GB
}

variable "db_engine_version" {
  type    = string  
  default = "17.6" 
}

variable "db_instance_class" {
  type    = string  
  default = "db.t4g.micro" 
}

variable "db_multi_az" {
  type    = bool    
  default = false 
}

variable "kms_key_id" {
  description = "KMS key ARN used for RDS encryption and Performance Insights"
  type        = string
  default     = "arn:aws:kms:eu-west-2:924609080268:key/19b9b692-72d7-4485-ae34-79defbfbc22a"
}

# Daily job schedule
variable "schedule_hour" {
  type    = string  
  default = "2" 
}

variable "schedule_minute" {
  type    = string  
  default = "15" 
}

variable "daily_schedule_timezone" {
  description = "IANA timezone for the daily schedule (DST handled)"
  type        = string
  default     = "Europe/London"
}

# ECS sizing
variable "ecs_web_cpu" {
  description = "CPU units for the main Django ECS task (Fargate). 1024 = 1 vCPU."
  type        = number
  default     = 512
}

variable "ecs_web_memory" {
  description = "Memory (MiB) for the main Django ECS task (Fargate)."
  type        = number
  default     = 1024
}

variable "ecs_cron_cpu" {
  description = "CPU units for the scheduled ECS task."
  type        = number
  default     = 256
}

variable "ecs_cron_memory" {
  description = "Memory (MiB) for the scheduled ECS task."
  type        = number
  default     = 512
}

# GitHub values
variable "gh_owner" {
  description = "GitHub organization or user name for OIDC deploy trust"
  type        = string
  default     = "NHSDigital"
}

variable "gh_repo" {
  description = "GitHub repository name for OIDC deploy trust"
  type        = string
  default     = "pps-weight-management"
}
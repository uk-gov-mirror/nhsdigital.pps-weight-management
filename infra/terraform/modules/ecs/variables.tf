variable "name" {
  description = "Resource name prefix"
  type        = string
}

variable "image_tag" {
  description = "Docker image tag"
  type        = string
  default     = "latest"
}

variable "cpu" {
  description = "CPU units"
  type        = string
  default     = "256"
}

variable "memory" {
  description = "Memory in MB"
  type        = string
  default     = "512"
}

variable "ephemeral_storage_gib" {
  description = "Optional ECS task ephemeral storage size in GiB (Fargate supports 21-200). Null uses AWS default (20 GiB)."
  type        = number
  default     = null

  validation {
    condition     = var.ephemeral_storage_gib == null || (var.ephemeral_storage_gib >= 21 && var.ephemeral_storage_gib <= 200)
    error_message = "ephemeral_storage_gib must be null or between 21 and 200 GiB."
  }
}

variable "docker_image" {
  description = "Docker image URI"
  type        = string
}

variable "db_username" {
  description = "DB username"
  type        = string
}

variable "db_address" {
  description = "DB address"
  type        = string
}

variable "db_password_secret_arn" {
  description = "ARN of the secret containing DB credentials"
  type        = string
}

variable "db_password_secret_key" {
  description = "Key inside the DB credentials secret JSON"
  type        = string
  default     = "password"
}

variable "db_endpoint" {
  description = "DB endpoint"
  type        = string
}

variable "db_name" {
  description = "DB name"
  type        = string
}

variable "django_secret_key" {
  description = "Django secret key"
  type        = string
  sensitive   = true
}

variable "region" {
  description = "AWS region"
  type        = string
}

variable "desired_count" {
  description = "Desired task count"
  type        = number
  default     = 1
}

variable "private_ecs_subnet_ids" {
  description = "Private ECS subnet IDs"
  type        = list(string)
}

variable "ecs_sg_id" {
  description = "ECS security group ID"
  type        = string
}

variable "target_group_arn" {
  description = "ALB target group ARN"
  type        = string
}

variable "tags" {
  description = "Tags"
  type        = map(string)
  default     = {}
}

variable "service_api_base_url" {
  description = "Internal base URL for API calls"
  type        = string
}
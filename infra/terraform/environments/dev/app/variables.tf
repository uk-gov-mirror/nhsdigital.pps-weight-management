variable "image_tag" {
  description = "Docker image tag to deploy"
  type        = string
  default     = "latest"
}

variable "environment" {
  description = "Target environment"
  type        = string
  default     = "poc"
}

variable "environment_suffix" {
  description = "Optional suffix for the environment"
  type        = string
  default     = "poc"
}
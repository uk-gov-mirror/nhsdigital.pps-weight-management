variable "name" {
  description = "Resource name prefix"
  type        = string
}

variable "django_secret_key" {
  description = "Django secret key"
  type        = string
  default     = "" # Use random if empty
}

variable "recovery_window" {
  description = "Recovery window in days"
  type        = number
  default     = 7
}

variable "tags" {
  description = "Tags for resources"
  type        = map(string)
  default     = {}
}
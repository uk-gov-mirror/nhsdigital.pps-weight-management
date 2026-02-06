variable "name" {
  description = "Name for the WAF Web ACL and associated resources."
  type        = string
}

variable "scope" {
  description = "Scope of the WAF Web ACL. Valid values: REGIONAL (for ALB/API Gateway) or CLOUDFRONT (must be in us-east-1)"
  type        = string
  default     = "REGIONAL"
  validation {
    condition     = contains(["REGIONAL", "CLOUDFRONT"], var.scope)
    error_message = "Scope must be either REGIONAL or CLOUDFRONT."
  }
}

variable "admin_ip_set_arn" {
  description = "The ARN of the IP set allowed to access admin paths. If provided, access to /admin/* is restricted to these IPs."
  type        = string
  default     = null
}

variable "tags" {
  description = "A map of tags to assign to the resources."
  type        = map(string)
  default     = {}
}
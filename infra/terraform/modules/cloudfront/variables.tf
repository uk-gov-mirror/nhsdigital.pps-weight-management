variable "name" {
  description = "Resource name prefix"
  type        = string
}

variable "alb_dns_name" {
  description = "ALB DNS name to use as CloudFront origin"
  type        = string
}

variable "custom_header_value" {
  description = "Custom header value to verify requests are coming from CloudFront"
  type        = string
  sensitive   = true
}

variable "price_class" {
  description = "CloudFront distribution price class"
  type        = string
  default     = "PriceClass_100"
}

variable "web_acl_id" {
  description = "WAF Web ACL ID to associate with CloudFront"
  type        = string
  default     = ""
}

variable "acm_certificate_arn" {
  description = "ACM certificate ARN for custom domain (must be in us-east-1)"
  type        = string
  default     = ""
}

variable "default_root_object" {
  description = "Default root object"
  type        = string
  default     = "index.html"
}

variable "default_ttl" {
  description = "Default TTL for cached objects"
  type        = number
  default     = 3600
}

variable "max_ttl" {
  description = "Maximum TTL for cached objects"
  type        = number
  default     = 86400
}

variable "geo_restriction_type" {
  description = "Geo restriction type (none, whitelist, blacklist)"
  type        = string
  default     = "whitelist"
}

variable "geo_restriction_locations" {
  description = "List of country codes for geo restriction"
  type        = list(string)
  default     = []
}

variable "aliases" {
  description = "List of CNAMEs (aliases) for the CloudFront distribution"
  type        = list(string)
  default     = []
}

variable "ordered_cache_behaviors" {
  description = "Ordered cache behaviors for specific path patterns"
  type = list(object({
    path_pattern         = string
    allowed_methods      = list(string)
    cached_methods       = list(string)
    forward_query_string = bool
    forward_headers      = list(string)
    forward_cookies      = string
    min_ttl              = number
    default_ttl          = number
    max_ttl              = number
  }))
  default = []
}

variable "custom_error_responses" {
  description = "Custom error responses"
  type = list(object({
    error_code            = number
    response_code         = number
    response_page_path    = string
    error_caching_min_ttl = number
  }))
  default = []
}

variable "tags" {
  description = "Tags to apply to resources"
  type        = map(string)
  default     = {}
}

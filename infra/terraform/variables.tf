variable "region" {
  type    = string
  default = "eu-west-2"
}
variable "project" { type = string }

variable "env" { type = string } # poc 

variable "domain_name" {
  type    = string
  default = ""
}
variable "api_zip_path" {
  type    = string
  default = "../../api.zip"
}

variable "daily_zip_path" {
  type    = string
  default = "../../daily.zip"
}

variable "gh_owner" { type = string }

variable "gh_repo" { type = string }

variable "schedule_hour" {
  description = "Hour of day (0-23) in the chosen timezone"
  type        = number
  default     = 2
}

variable "schedule_minute" {
  description = "Minute of hour (0-59) in the chosen timezone"
  type        = number
  default     = 0
}
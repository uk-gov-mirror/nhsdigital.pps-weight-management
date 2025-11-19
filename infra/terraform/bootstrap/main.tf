####################################################################
#
# Use Terraform backend
# ---------------------
#
# Phase 1: use local backend on first apply
# Phase 2: switch to s3 backend by running init -reconfigure
#
#
####################################################################

terraform {
  required_version = ">= 1.6"

  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 6.0"
    }
  }

  backend "s3" {}
}

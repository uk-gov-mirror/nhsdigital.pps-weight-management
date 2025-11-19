####################################################################
#
# Terraform AWS Configuration for PPS Weight Management
# -----------------------------------------------------
# 
# - Each environment has it's own terraform.tfvars variables definition file in /envs/{environment}
# - Terraform state is stored in the S3 instance created in /bootstrap/backend.tf
# 
# Run this script after each infrastructure change (example for poc environemnt)
# 
# > cd infra/terraform
# > terraform init -backend-config="bucket=nhse-pps-wm-terraform-state-bucket" -backend-config="key=poc/terraform.tfstate" -backend-config="region=eu-west-2"
# > terraform apply -auto-approve -var-file="envs/poc/terraform.tfvars"
# 
# Infrastrcuture created
#  
#                     +-------------------------------------+
#                     |           (Public Internet)         |
#                     +--------------------+----------------+
#                                          |
#                                          v
# +-----------------------+       only CloudFront        +-----------------------+
# |  AWS WAF (CLOUDFRONT) | <==========================> |  Amazon CloudFront    |
# |  Web ACL: site_waf    |                              |  (distribution)*      |
# +-----------+-----------+                              +-----------+-----------+
#             | (filters)                                             |
#             |                                                       v
#             |                                        +-------------------------------+
#             |  allows only CloudFront prefix list    |  Application Load Balancer    |
#             +--------------------------------------> |  (ALB) in PUBLIC subnets      |
#                                                      |  SG: alb                      |
#                                                      +-------+-----------------------+
#                                                              |
#                                               HTTP:80 -> TG  | forwards to target group
#                                                              v
# +---------------------------------------------------------------------------------------------+
# |                                  VPC (from module.vpc)                                      |
# |                                                                                             |
# |  Subnets:                                                                                   |
# |    - PUBLIC  : ALB                                                                          |
# |    - PRIVATE : ECS tasks, RDS                                                               |
# |                                                                                             |
# |   +-----------------------------------+                  +--------------------------------+ |
# |   |  ECS Cluster: app                 |                  |  RDS: PostgreSQL (pg)          | |
# |   |  Service: web (FARGATE)           |                  |  DB Subnet Group: private      | |
# |   |  TaskDef: django (container 'web')|                  |  SG: db                        | |
# |   |  SG: svc                          |                  |  Not publicly accessible       | |
# |   |  - Receives from ALB target group |                  |  - Allows ingress from SG svc  | |
# |   |  - No public IP (awsvpc)          |                  +--------------------------------+ |
# |   |                                   |                                                     |
# |   +---------------------+-------------+                                                     |
# |                         |                                                                   |
# |                         | uses image from                                                   |
# |                         v                                                                   |
# |              +------------------------+                                                     |
# |              | Amazon ECR: django repo |  <-- Images pushed by CI via IAM OIDC role         |
# |              +------------------------+                                                     |
# |                                                                                             |
# |   Scheduled jobs (private subnets, no public IP):                                           |
# |   +-----------------------------------+                                                     |
# |   |  EventBridge Scheduler (daily)    | --> runs --> Fargate TaskDef: cron (container 'job')|
# |   |  IAM role: scheduler_run_ecs      |       in ECS Cluster: app, SG: svc                  |
# |   +-----------------------------------+                                                     |
# +---------------------------------------------------------------------------------------------+
# 
# Version History:
#
# Date       | Comment
# -----------+----------------------------------------------------
# 2025-09-05 | Initial version
# 2025-09-14 | Added Event Scheduler
# 2025-11-05 | Refactored to switch to Jinja/Django/Postgres
# 2025-11-19 | Refactored to move networking components into network.tf
#
####################################################################

############################################
# Terraform and AWS Provider Configuration
############################################
# Defines the required Terraform version and providers.
# Configure the S3 backend for remote state management,
# which is crucial for collaborative development.
############################################

terraform {
  required_version = ">= 1.6"

  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
    random = {
      source  = "hashicorp/random"
      version = "~> 3.6"
    }
  }

  backend "s3" {
    bucket       = "nhse-pps-wm-terraform-state-bucket"
    use_lockfile = true
    encrypt      = true
    # key/region configured via -backend-config in init command
  }
}

############################
# Providers
############################

provider "aws" {
  region = var.region
  default_tags {
    tags = {
      Project = "${var.project}-${var.env}"
    }
  }
}

# Shared infrastructure from bootstrap
data "terraform_remote_state" "bootstrap" {
  backend = "s3"
  config = {
    bucket = "nhse-pps-wm-terraform-state-bucket"
    key    = "bootstrap/terraform.tfstate"
    region = var.region
  }
}

# CloudFront/WAF live in us-east-1
provider "aws" {
  alias  = "us-east-1"
  region = "us-east-1"
  default_tags {
    tags = {
      Project = "${var.project}-${var.env}"
    }
  }
}

############################
# Data sources
############################

data "aws_caller_identity" "current" {}
data "aws_region" "current" {}
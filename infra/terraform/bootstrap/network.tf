####################################################################
#
# Shared network + base app resources
# -----------------------------------
#
# Run once to create:
# - A shared VPC and subnets
# - A shared ECS cluster
# - A shared ECR repository for the Django image
#
# > cd infra/terraform/bootstrap
# > terraform init
# > terraform apply -auto-approve -var 'project=nhse-pps-wm'
#
####################################################################

provider "aws" {
  region = "eu-west-2"
}

variable "project" {
  description = "Short project identifier used for naming shared resources"
  type        = string
}

# VPC inputs (same defaults as main variables.tf)
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

############################
# Shared VPC
############################

module "vpc" {
  source  = "terraform-aws-modules/vpc/aws"
  version = "~> 5.0"

  # NOTE: no env suffix here – this is a single shared VPC
  name = "${var.project}-shared-vpc"
  cidr = var.vpc_cidr
  azs  = var.azs

  public_subnets  = var.public_subnet_cidrs
  private_subnets = var.private_subnet_cidrs

  enable_dns_hostnames = true
  enable_dns_support   = true

  manage_default_network_acl    = false
  manage_default_security_group = false

  enable_nat_gateway = true
  single_nat_gateway = true

  public_subnet_tags = {
    "kubernetes.io/role/elb" = "1"
  }

  private_subnet_tags = {
    "kubernetes.io/role/internal-elb" = "1"
  }
}

############################
# Shared ECS cluster
############################

resource "aws_ecs_cluster" "app" {
  name = "${var.project}-ecs"
}

############################
# Shared ECR repository
############################

resource "aws_ecr_repository" "django" {
  name                 = "${var.project}-django"
  force_delete         = true
  image_tag_mutability = "MUTABLE"

  image_scanning_configuration {
    scan_on_push = true
  }
}

############################
# Outputs for env stacks
############################

output "vpc_id" {
  description = "ID of the shared VPC"
  value       = module.vpc.vpc_id
}

output "public_subnets" {
  description = "IDs of the shared public subnets"
  value       = module.vpc.public_subnets
}

output "private_subnets" {
  description = "IDs of the shared private subnets"
  value       = module.vpc.private_subnets
}

output "ecr_repository_url" {
  description = "URL of the shared ECR repository for the Django image"
  value       = aws_ecr_repository.django.repository_url
}

output "ecs_cluster_arn" {
  description = "ARN of the shared ECS cluster"
  value       = aws_ecs_cluster.app.arn
}

output "ecs_cluster_name" {
  description = "Name of the shared ECS cluster"
  value       = aws_ecs_cluster.app.name
}

locals {
  project        = "pps-htsh"
  environment    = "poc"
  context_string = "${local.project}-${local.environment}"

  admin_ip_addresses = [
    "147.161.224.177/32",
    "172.187.228.0/24",
    "20.39.229.0/24",
    "136.226.191.99/32",
    "51.7.207.149/32"
  ]
}

module "vpc" {
  source = "git::https://github.com/terraform-aws-modules/terraform-aws-vpc.git?ref=26c38a66f12e7c6c93b6a2ba127ad68981a48671"

  name = "${local.context_string}-vpc"
  cidr = "10.0.0.0/16"

  azs             = ["eu-west-2a", "eu-west-2b"]
  public_subnets  = ["10.0.1.0/24", "10.0.4.0/24"]
  private_subnets = ["10.0.2.0/24", "10.0.3.0/24"]

  enable_nat_gateway = true
  single_nat_gateway = true

  tags = {
    Project     = local.project
    Environment = local.environment
  }
}

module "flow_log" {
  source = "git::https://github.com/terraform-aws-modules/terraform-aws-vpc.git//modules/flow-log?ref=26c38a66f12e7c6c93b6a2ba127ad68981a48671"

  name   = "${local.context_string}-flow-log"
  vpc_id = module.vpc.vpc_id

  tags = {
    Project     = local.project
    Environment = local.environment
  }
}

module "security_groups" {
  source = "../../../modules/security_groups"
  vpc_id = module.vpc.vpc_id
  name   = local.context_string
}

resource "aws_wafv2_ip_set" "admin_ipset" {
  name               = "${local.context_string}-admin-ipset"
  description        = "Whitelisted IPs for /admin/ access"
  scope              = "CLOUDFRONT"
  ip_address_version = "IPV4"
  addresses          = local.admin_ip_addresses

  provider = aws.us_east_1

  tags = {
    Project     = local.project
    Environment = local.environment
  }
}

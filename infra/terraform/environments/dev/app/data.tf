data "aws_vpc" "network" {
  tags = {
    Name = "${local.project}-${local.environment}-vpc"
  }
}

data "aws_subnets" "public" {
  filter {
    name   = "vpc-id"
    values = [data.aws_vpc.network.id]
  }

  tags = {
    Name = "*public*"
  }
}

data "aws_subnets" "private_ecs" {
  filter {
    name   = "vpc-id"
    values = [data.aws_vpc.network.id]
  }

  tags = {
    Name = "*private*"
  }
}

data "aws_route53_zone" "main" {
  name         = "help-to-stay-healthy-pilot.service.nhs.uk"
  private_zone = false
}

data "aws_security_group" "alb" {
  vpc_id = data.aws_vpc.network.id
  name   = "${local.project}-${local.environment}-alb-sg"
}

data "aws_security_group" "ecs" {
  vpc_id = data.aws_vpc.network.id
  name   = "${local.project}-${local.environment}-ecs-sg"
}

data "aws_db_instance" "datastore" {
  db_instance_identifier = "${local.project}-${local.environment}-rds"
}

data "aws_secretsmanager_secret_version" "secrets" {
  secret_id = "${local.project}-${local.environment}-secrets-manager"
}

data "aws_wafv2_ip_set" "admin_ipset" {
  name     = "${local.project}-${local.environment}-admin-ipset"
  scope    = "CLOUDFRONT"
  provider = aws.us_east_1
}
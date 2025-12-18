data "aws_vpc" "network" {
  tags = {
    Name = "${local.context_string}-vpc"
  }
}

data "aws_subnets" "private_rds" {
  filter {
    name   = "vpc-id"
    values = [data.aws_vpc.network.id]
  }

  tags = {
    Name = "*private*"
  }
}

data "aws_security_group" "rds" {
  vpc_id = data.aws_vpc.network.id
  name   = "${local.context_string}-rds-sg"
}

data "aws_secretsmanager_secret_version" "db_password" {
  secret_id = "${local.context_string}-secrets-manager"
}
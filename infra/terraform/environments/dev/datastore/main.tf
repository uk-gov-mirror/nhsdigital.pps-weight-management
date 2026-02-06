locals {
  project        = "pps-htsh"
  environment    = "poc"
  context_string = "${local.project}-${local.environment}"
}

module "rds" {
  source = "../../../modules/rds"

  name                   = local.context_string
  db_name                = "ppswmdev"
  db_username            = "ppswmuser"
  db_password            = jsondecode(data.aws_secretsmanager_secret_version.db_password.secret_string)["db_password"]
  private_rds_subnet_ids = data.aws_subnets.private_rds.ids
  rds_sg_id              = data.aws_security_group.rds.id
  instance_class         = "db.t3.micro"
  multi_az               = false
  deletion_protection    = false

  tags = {
    Project     = local.project
    Environment = local.environment
  }
}
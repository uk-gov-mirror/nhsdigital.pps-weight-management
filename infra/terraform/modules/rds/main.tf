resource "aws_db_parameter_group" "postgres" {
  family = "postgres15"
  name   = "${var.name}-pg"

  parameter {
    name  = "rds.force_ssl"
    value = "1"
  }
}

module "rds" {
  source  = "terraform-aws-modules/rds/aws"
  version = "~> 6.0"

  identifier = "${var.name}-rds"

  engine               = "postgres"
  engine_version       = "15"
  family               = "postgres15"
  major_engine_version = "15"
  instance_class       = var.instance_class

  allocated_storage     = var.allocated_storage
  max_allocated_storage = var.max_allocated_storage

  db_name  = var.db_name
  username = var.db_username
  password = var.db_password
  port     = 5432

  multi_az               = var.multi_az
  db_subnet_group_name   = aws_db_subnet_group.main.name
  vpc_security_group_ids = [var.rds_sg_id]

  maintenance_window              = "Mon:00:00-Mon:03:00"
  backup_window                   = "03:00-06:00"
  enabled_cloudwatch_logs_exports = ["postgresql"]
  create_cloudwatch_log_group     = true

  backup_retention_period = var.backup_retention_period
  skip_final_snapshot     = var.skip_final_snapshot
  deletion_protection     = var.deletion_protection

  parameter_group_name = aws_db_parameter_group.postgres.name

  tags = var.tags
}

resource "aws_db_subnet_group" "main" {
  name       = "${var.name}-rds-subnet-group"
  subnet_ids = var.private_rds_subnet_ids

  tags = var.tags
}
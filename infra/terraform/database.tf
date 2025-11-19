############################################
# RDS PostgreSQL
############################################

resource "aws_db_subnet_group" "pg" {
  name       = "${var.project}-${var.env}-pg-subnets"
  subnet_ids = data.terraform_remote_state.bootstrap.outputs.private_subnets
}

resource "random_password" "db_password" {
  length      = 24
  special     = false
  min_upper   = 1
  min_lower   = 1
  min_numeric = 1
}

resource "aws_ssm_parameter" "db_username" {
  name  = "/${var.project}/${var.env}/db/username"
  type  = "String"
  value = var.db_username
}

resource "aws_ssm_parameter" "db_password" {
  name  = "/${var.project}/${var.env}/db/password"
  type  = "SecureString"
  value = random_password.db_password.result
}

resource "aws_db_instance" "pg" {
  identifier       = "${var.project}-${var.env}-pg"

  engine           = "postgres"
  engine_version   = var.db_engine_version # 17.6
  instance_class   = var.db_instance_class # db.t4g.micro

  # storage profile
  storage_type        = "gp2"
  allocated_storage   = 20
  publicly_accessible = false
  backup_retention_period = 1

  # encryption + KMS
  storage_encrypted   = true
  kms_key_id          = var.kms_key_id

  # Performance Insights (often enforced)
  performance_insights_enabled           = true
  performance_insights_kms_key_id        = var.kms_key_id
  performance_insights_retention_period  = 7

  # networking
  db_subnet_group_name   = aws_db_subnet_group.pg.name
  vpc_security_group_ids = [aws_security_group.db.id]

  # credentials
  db_name   = var.db_name
  username  = var.db_username
  password  = random_password.db_password.result

  # lifecycle
  deletion_protection  = false
  skip_final_snapshot  = true

  # If your org enforces request-time tags, uncomment and adjust:
  # tags = {
  #   Project     = "${var.project}-${var.env}"
  #   Environment = var.env
  #   Owner       = "YourTeam"
  # }
}
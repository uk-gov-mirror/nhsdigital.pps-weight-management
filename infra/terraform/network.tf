############################
# VPC (terraform-aws-modules/vpc)
############################

# CloudFront origin-facing IPv4 managed prefix list
data "aws_ec2_managed_prefix_list" "cloudfront_origin" {
  name = "com.amazonaws.global.cloudfront.origin-facing"
}

# ALB -> public 80 (switch to 443 once you add ACM/TLS on ALB)
resource "aws_security_group" "alb" {
  name        = "${var.project}-${var.env}-alb-sg"
  description = "ALB ingress"
  vpc_id      = data.terraform_remote_state.bootstrap.outputs.vpc_id

  ingress {
    description     = "Only CloudFront to ALB (HTTP)"
    from_port       = 80
    to_port         = 80
    protocol        = "tcp"
    prefix_list_ids = [data.aws_ec2_managed_prefix_list.cloudfront_origin.id]
  }
  egress  { 
    from_port   = 0  
	to_port     = 0  
	protocol    = "-1"  
	cidr_blocks = ["0.0.0.0/0"] 
  }
}

# Service SG (only ALB may call it)
resource "aws_security_group" "svc" {
  name        = "${var.project}-${var.env}-svc-sg"
  description = "ECS service ingress from ALB"
  vpc_id      = data.terraform_remote_state.bootstrap.outputs.vpc_id

  ingress {
    from_port       = var.django_container_port
    to_port         = var.django_container_port
    protocol        = "tcp"
    security_groups = [aws_security_group.alb.id]
  }
  egress  { 
    from_port   = 0 
	to_port     = 0 
	protocol    = "-1" 
	cidr_blocks = ["0.0.0.0/0"] 
  }
}

# DB SG (only app service may connect)
resource "aws_security_group" "db" {
  name        = "${var.project}-${var.env}-db-sg"
  description = "PostgreSQL ingress from app"
  vpc_id      = data.terraform_remote_state.bootstrap.outputs.vpc_id

  ingress {
    from_port       = 5432
    to_port         = 5432
    protocol        = "tcp"
    security_groups = [aws_security_group.svc.id]
  }
  egress  { 
    from_port   = 0 
	to_port     = 0 
	protocol    = "-1" 
	cidr_blocks = ["0.0.0.0/0"] 
  }
}

# --- SSM bastion SG (no inbound, all outbound) ---
resource "aws_security_group" "ssm_bastion" {
  name   = "${var.project}-${var.env}-ssm-bastion-sg"
  vpc_id = data.terraform_remote_state.bootstrap.outputs.vpc_id

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = { Name = "${var.project}-${var.env}-ssm-bastion-sg" }
}

# --- Permit the bastion to reach Postgres on the existing DB SG ---
resource "aws_security_group_rule" "db_ingress_from_bastion" {
  type                     = "ingress"
  from_port                = 5432
  to_port                  = 5432
  protocol                 = "tcp"
  security_group_id        = aws_security_group.db.id           
  source_security_group_id = aws_security_group.ssm_bastion.id  
}

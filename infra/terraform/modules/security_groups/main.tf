data "aws_ec2_managed_prefix_list" "cloudfront_origin_facing" {
  name = "com.amazonaws.global.cloudfront.origin-facing"
}

resource "aws_security_group" "alb" {
  #checkov:skip=CKV2_AWS_5: SG is attached by consuming modules/resources via exported output `alb_sg_id`.
  name        = "${var.name}-alb-sg"
  description = "Controls inbound CloudFront traffic to ALB"
  vpc_id      = var.vpc_id

  ingress {
    description     = "Allow HTTP from CloudFront origin-facing managed prefix list"
    from_port       = 80
    to_port         = 80
    protocol        = "tcp"
    prefix_list_ids = [data.aws_ec2_managed_prefix_list.cloudfront_origin_facing.id]
  }

  ingress {
    description     = "Allow HTTPS from CloudFront origin-facing managed prefix list"
    from_port       = 443
    to_port         = 443
    protocol        = "tcp"
    prefix_list_ids = [data.aws_ec2_managed_prefix_list.cloudfront_origin_facing.id]
  }

  egress {
    description     = "Allow ALB to reach ECS service on HTTP"
    from_port       = 80
    to_port         = 80
    protocol        = "tcp"
    security_groups = [aws_security_group.ecs.id]
  }
}

resource "aws_security_group" "ecs" {
  #checkov:skip=CKV2_AWS_5: SG is attached by consuming modules/resources via exported output `ecs_sg_id`.
  name        = "${var.name}-ecs-sg"
  description = "Controls inbound and outbound traffic for ECS tasks"
  vpc_id      = var.vpc_id

  ingress {
    description     = "Allow app traffic from ALB"
    from_port       = 0
    to_port         = 65535
    protocol        = "tcp"
    security_groups = [aws_security_group.alb.id]
  }

  egress {
    description = "Allow HTTPS egress for AWS API access"
    from_port   = 443
    to_port     = 443
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  egress {
    description     = "Allow ECS tasks to connect to RDS"
    from_port       = 5432
    to_port         = 5432
    protocol        = "tcp"
    security_groups = [aws_security_group.rds.id]
  }
}

resource "aws_security_group" "rds" {
  name        = "${var.name}-rds-sg"
  description = "Controls database access for RDS"
  vpc_id      = var.vpc_id

  ingress {
    description     = "Allow PostgreSQL from ECS tasks"
    from_port       = 5432
    to_port         = 5432
    protocol        = "tcp"
    security_groups = [aws_security_group.ecs.id]
  }

  egress {
    description     = "Allow response traffic to ECS tasks"
    from_port       = 5432
    to_port         = 5432
    protocol        = "tcp"
    security_groups = [aws_security_group.ecs.id]
  }
}

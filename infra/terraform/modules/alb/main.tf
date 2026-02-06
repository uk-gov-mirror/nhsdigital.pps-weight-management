module "alb" {
  source  = "terraform-aws-modules/alb/aws"
  version = "~> 9.0"

  name    = "${var.name}-alb"
  vpc_id  = var.vpc_id
  subnets = var.public_subnet_ids

  security_groups = [var.alb_sg_id]

  enable_deletion_protection = false

  listeners = {
    http = {
      port     = 80
      protocol = "HTTP"
      forward = {
        target_group_key = "ecs"
      }
    }
  }

  target_groups = {
    ecs = {
      name_prefix       = "ecs-"
      protocol          = "HTTP"
      port              = 80
      target_type       = "ip"
      vpc_id            = var.vpc_id
      create_attachment = false
      health_check = {
        enabled             = true
        healthy_threshold   = 2
        interval            = 30
        matcher             = "200"
        path                = "/health" # Django health check
        port                = "traffic-port"
        protocol            = "HTTP"
        timeout             = 5
        unhealthy_threshold = 2
      }
    }
  }

  tags = var.tags
}
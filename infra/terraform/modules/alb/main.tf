module "alb" {
  source = "git::https://github.com/terraform-aws-modules/terraform-aws-alb.git?ref=222bae0825c4fabf6f91f4652511fa5953bc9c73"

  name    = "${var.name}-alb"
  vpc_id  = var.vpc_id
  subnets = var.public_subnet_ids

  security_groups = [var.alb_sg_id]

  enable_deletion_protection = false

  listeners = {
    http_listener = {
      port     = 80
      protocol = "HTTP"

      fixed_response = {
        content_type = "text/plain"
        message_body = "Access Denied"
        status_code  = "401"
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

resource "aws_lb_listener_rule" "cloudfront_header" {
  listener_arn = module.alb.listeners["http_listener"].arn
  priority     = 100

  condition {
    http_header {
      http_header_name = "X-Custom-Header"
      values           = [var.custom_header_value]
    }
  }

  action {
    type             = "forward"
    target_group_arn = module.alb.target_groups["ecs"].arn
  }

  tags = var.tags
}
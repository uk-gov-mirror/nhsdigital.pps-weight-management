############################################
# ECS Fargate (Django)
############################################

resource "aws_cloudwatch_log_group" "django" {
  name              = "/ecs/${var.project}-${var.env}-django"
  retention_in_days = 30
}

# Task/execution roles
data "aws_iam_policy_document" "ecs_task_assume" {
  statement {
    actions = ["sts:AssumeRole"]
    principals { 
	  type = "Service" 
	  identifiers = ["ecs-tasks.amazonaws.com"] 
	}
  }
}

resource "aws_iam_role" "ecs_task_execution" {
  name               = "${var.project}-${var.env}-ecs-exec"
  assume_role_policy = data.aws_iam_policy_document.ecs_task_assume.json
}

resource "aws_iam_role_policy_attachment" "ecs_exec_policy" {
  role       = aws_iam_role.ecs_task_execution.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AmazonECSTaskExecutionRolePolicy"
}

resource "aws_iam_role" "ecs_task" {
  name               = "${var.project}-${var.env}-ecs-task"
  assume_role_policy = data.aws_iam_policy_document.ecs_task_assume.json
}

resource "aws_iam_role_policy" "ecs_exec_ssm_params" {
  name = "ecs-exec-ssm-params"
  role = aws_iam_role.ecs_task_execution.name   # attach to your existing role

  policy = jsonencode({
    Version = "2012-10-17",
    Statement = [
      {
        Sid      = "AllowReadSSMParameters"
        Effect   = "Allow"
        Action   = [
          "ssm:GetParameter",
          "ssm:GetParameters"
        ]
        Resource = "arn:aws:ssm:eu-west-2:${data.aws_caller_identity.current.account_id}:parameter/${var.project}/${var.env}/*"
      },
      {
        Sid      = "AllowKMSDecryptForSecureStrings"
        Effect   = "Allow"
        Action   = ["kms:Decrypt"]
        Resource = "*"  # or restrict to your KMS key if you prefer
      }
    ]
  })
}

resource "aws_iam_role_policy_attachment" "ecs_exec_base" {
  role       = aws_iam_role.ecs_task_execution.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AmazonECSTaskExecutionRolePolicy"
}

# Execution role needs to read SSM params for ECS "secrets" injection
data "aws_iam_policy_document" "ecs_exec_ssm_read" {
  statement {
    actions = [
      "ssm:GetParameter",
      "ssm:GetParameters",
    ]
    resources = [
      aws_ssm_parameter.cognito_client_id.arn,
      aws_ssm_parameter.cognito_user_pool_id.arn,
      aws_ssm_parameter.aws_region.arn,
      aws_ssm_parameter.db_password.arn, # you already inject this too
    ]
  }

  # Needed if any injected parameter is SecureString
  statement {
    actions   = ["kms:Decrypt"]
    resources = ["*"]
    condition {
      test     = "StringEquals"
      variable = "kms:ViaService"
      values   = ["ssm.${var.region}.amazonaws.com"]
    }
  }
}

resource "aws_iam_policy" "ecs_exec_ssm_read" {
  name   = "${var.project}-${var.env}-ecs-exec-ssm-read"
  policy = data.aws_iam_policy_document.ecs_exec_ssm_read.json
}

resource "aws_iam_role_policy_attachment" "ecs_exec_ssm_read" {
  role       = aws_iam_role.ecs_task_execution.name
  policy_arn = aws_iam_policy.ecs_exec_ssm_read.arn
}

# Web task definition
resource "aws_ecs_task_definition" "django" {
  family                   = "${var.project}-${var.env}-django"
  requires_compatibilities = ["FARGATE"]
  network_mode             = "awsvpc"
  cpu                      = var.ecs_web_cpu
  memory                   = var.ecs_web_memory
  execution_role_arn       = aws_iam_role.ecs_task_execution.arn
  task_role_arn            = aws_iam_role.ecs_task.arn

  container_definitions = jsonencode([
    {
      name      = "web"
      image     = "${data.terraform_remote_state.bootstrap.outputs.ecr_repository_url}:${var.django_image_tag}"
      essential = true
      portMappings = [{ containerPort = var.django_container_port, hostPort = var.django_container_port, protocol = "tcp" }]
      environment = [
        { name = "DATABASE_HOST",         value = aws_db_instance.pg.address },
        { name = "DATABASE_PORT",         value = "5432" },
        { name = "DATABASE_NAME",         value = var.db_name },
        { name = "DATABASE_USER",         value = var.db_username }
      ]
      secrets = [
        { name = "DATABASE_PASSWORD"   , valueFrom = aws_ssm_parameter.db_password.arn },
        { name = "COGNITO_CLIENT_ID"   , valueFrom = aws_ssm_parameter.cognito_client_id.arn },
        { name = "COGNITO_USER_POOL_ID", valueFrom = aws_ssm_parameter.cognito_user_pool_id.arn },
        { name = "AWS_REGION"          , valueFrom = aws_ssm_parameter.aws_region.arn }
      ]
      logConfiguration = {
        logDriver = "awslogs"
        options = {
          awslogs-group         = "/ecs/${var.project}-${var.env}-django"
          awslogs-region        = "eu-west-2"
          awslogs-stream-prefix = "web"
        }
      }
    }
  ])
}

############################################
# Application Load Balancer
############################################

# ALB + target group + listener
resource "aws_lb" "app" {
  name               = "${var.project}-${var.env}-alb"
  load_balancer_type = "application"
  internal           = false
  subnets            = data.terraform_remote_state.bootstrap.outputs.public_subnets
  security_groups    = [aws_security_group.alb.id]
}

resource "aws_lb_target_group" "app" {
  name        = "${var.project}-${var.env}-tg"
  port        = var.django_container_port
  protocol    = "HTTP"
  vpc_id      = data.terraform_remote_state.bootstrap.outputs.vpc_id
  target_type = "ip"

  health_check {
    path                = "/health"
    matcher             = "200-399"
    interval            = 30
    timeout             = 5
    healthy_threshold   = 2
    unhealthy_threshold = 5
  }
}

resource "aws_lb_listener" "http" {
  load_balancer_arn = aws_lb.app.arn
  port              = 80
  protocol          = "HTTP"

  default_action {
    type             = "forward"
    target_group_arn = aws_lb_target_group.app.arn
  }
}

############################################
# ECS Service
############################################

resource "aws_ecs_service" "web" {
  name            = "${var.project}-${var.env}-web"
  cluster         = data.terraform_remote_state.bootstrap.outputs.ecs_cluster_arn
  task_definition = aws_ecs_task_definition.django.arn
  desired_count   = 2
  launch_type     = "FARGATE"

  network_configuration {
    assign_public_ip = false
    subnets          = data.terraform_remote_state.bootstrap.outputs.private_subnets
    security_groups  = [aws_security_group.svc.id]
  }

  load_balancer {
    target_group_arn = aws_lb_target_group.app.arn
    container_name   = "web"
    container_port   = var.django_container_port
  }

  depends_on = [aws_lb_listener.http]
}
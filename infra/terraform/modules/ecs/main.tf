resource "aws_ecs_cluster" "main" {
  name = "${var.name}-cluster"

  setting {
    name  = "containerInsights"
    value = "enabled"
  }

  tags = var.tags
}

resource "aws_ecs_task_definition" "app" {
  family                   = "${var.name}-app"
  network_mode             = "awsvpc"
  requires_compatibilities = ["FARGATE"]
  cpu                      = var.cpu
  memory                   = var.memory
  execution_role_arn       = aws_iam_role.execution.arn
  task_role_arn            = aws_iam_role.task.arn

  container_definitions = jsonencode([
    {
      name                   = "web"
      image                  = "${var.docker_image}:${var.image_tag}"
      essential              = true
      readonlyRootFilesystem = true
      linuxParameters = {
        initProcessEnabled = true
      }
      portMappings = [{ containerPort = 8000, hostPort = 8000, protocol = "tcp" }]
      environment = [
        { name = "DATABASE_HOST", value = var.db_address },
        { name = "DATABASE_PORT", value = "5432" },
        { name = "DATABASE_NAME", value = var.db_name },
        { name = "DATABASE_USER", value = var.db_username },
        { name = "DATABASE_PASSWORD_SECRET_ARN", value = var.db_password_secret_arn },
        { name = "DATABASE_PASSWORD_SECRET_KEY", value = var.db_password_secret_key },
        { name = "SERVICE_API_BASE_URL", value = var.service_api_base_url },
        { name = "AWS_REGION", value = "eu-west-2" },
        { name = "PGSSLMODE", value = "require" }
      ]
      secrets = [
        { name = "DJANGO_SECRET_KEY", valueFrom = var.django_secret_key }
        # { name = "COGNITO_CLIENT_ID"   , valueFrom = aws_ssm_parameter.cognito_client_id.arn },
        # { name = "COGNITO_USER_POOL_ID", valueFrom = aws_ssm_parameter.cognito_user_pool_id.arn },
      ]
      logConfiguration = {
        logDriver = "awslogs"
        options = {
          awslogs-group         = "/ecs/${var.name}-app"
          awslogs-region        = "eu-west-2"
          awslogs-stream-prefix = "web"
        }
      }
    }
  ])
  tags = var.tags
}

resource "aws_ecs_service" "app" {
  name                   = "${var.name}-service"
  cluster                = aws_ecs_cluster.main.id
  task_definition        = aws_ecs_task_definition.app.arn
  desired_count          = var.desired_count
  launch_type            = "FARGATE"
  enable_execute_command = true

  network_configuration {
    security_groups  = [var.ecs_sg_id]
    subnets          = var.private_ecs_subnet_ids
    assign_public_ip = false
  }

  load_balancer {
    target_group_arn = var.target_group_arn
    container_name   = "web"
    container_port   = 8000
  }

  # Wait for target group to be ready before creating service
  depends_on = [var.target_group_arn]

  # Prevent replacement when service is being drained
  lifecycle {
    create_before_destroy = false
  }

  tags = var.tags
}

resource "aws_iam_role" "execution" {
  name = "${var.name}-ecs-execution-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = "sts:AssumeRole"
        Effect = "Allow"
        Principal = {
          Service = "ecs-tasks.amazonaws.com"
        }
      }
    ]
  })
}

resource "aws_iam_role_policy_attachment" "execution" {
  role       = aws_iam_role.execution.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AmazonECSTaskExecutionRolePolicy"
}

resource "aws_iam_role_policy" "execution_secrets" {
  name = "${var.name}-ecs-execution-secrets"
  role = aws_iam_role.execution.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "secretsmanager:GetSecretValue"
        ]
        Resource = [
          var.db_password_secret_arn,
          var.django_secret_key
        ]
      }
    ]
  })
}

resource "aws_iam_role" "task" {
  name = "${var.name}-ecs-task-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = "sts:AssumeRole"
        Effect = "Allow"
        Principal = {
          Service = "ecs-tasks.amazonaws.com"
        }
      }
    ]
  })
}

resource "aws_iam_role_policy" "task_ssm" {
  name = "${var.name}-ecs-task-ssm"
  role = aws_iam_role.task.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "ssmmessages:CreateControlChannel",
          "ssmmessages:CreateDataChannel",
          "ssmmessages:OpenControlChannel",
          "ssmmessages:OpenDataChannel"
        ]
        Resource = ["*"]
      }
    ]
  })
}

resource "aws_iam_role_policy" "task_db_secret" {
  name = "${var.name}-ecs-task-db-secret"
  role = aws_iam_role.task.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "secretsmanager:GetSecretValue"
        ]
        Resource = [var.db_password_secret_arn]
      },
      {
        Effect = "Allow"
        Action = [
          "kms:Decrypt"
        ]
        Resource = ["*"]
        Condition = {
          StringEquals = {
            "kms:ViaService" = "secretsmanager.${var.region}.amazonaws.com"
          }
        }
      }
    ]
  })
}

data "aws_caller_identity" "current" {}

data "aws_iam_policy_document" "ecs_logs_kms" {
  statement {
    sid    = "EnableRootPermissions"
    effect = "Allow"

    principals {
      type        = "AWS"
      identifiers = ["arn:aws:iam::${data.aws_caller_identity.current.account_id}:root"]
    }

    actions   = ["kms:*"]
    resources = ["*"]
  }

  statement {
    sid    = "AllowCloudWatchLogsUse"
    effect = "Allow"

    principals {
      type        = "Service"
      identifiers = ["logs.${var.region}.amazonaws.com"]
    }

    actions = [
      "kms:Encrypt",
      "kms:Decrypt",
      "kms:ReEncrypt*",
      "kms:GenerateDataKey*",
      "kms:DescribeKey"
    ]

    resources = ["*"]
  }
}

resource "aws_kms_key" "ecs_logs" {
  description         = "KMS key for ECS CloudWatch log group encryption"
  enable_key_rotation = true
  policy              = data.aws_iam_policy_document.ecs_logs_kms.json
}

resource "aws_cloudwatch_log_group" "ecs" {
  name              = "/ecs/${var.name}-app"
  retention_in_days = 365
  kms_key_id        = aws_kms_key.ecs_logs.arn

  tags = var.tags
}
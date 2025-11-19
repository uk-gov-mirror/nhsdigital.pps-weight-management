############################################
# Daily job: EventBridge Scheduler -> ECS RunTask
############################################

# Separate task definition for the scheduled job (reuse the same image)
resource "aws_ecs_task_definition" "cron" {
  family                   = "${var.project}-${var.env}-cron"
  requires_compatibilities = ["FARGATE"]
  network_mode             = "awsvpc"
  cpu                      = var.ecs_cron_cpu
  memory                   = var.ecs_cron_memory
  execution_role_arn       = aws_iam_role.ecs_task_execution.arn
  task_role_arn            = aws_iam_role.ecs_task.arn

  container_definitions = jsonencode([
    {
      name      = "job",
      image     = "${data.terraform_remote_state.bootstrap.outputs.ecr_repository_url}:${var.django_image_tag}",
      essential = true,
      environment = [
        { name = "DATABASE_HOST", value = aws_db_instance.pg.address },
        { name = "DATABASE_PORT", value = "5432" },
        { name = "DATABASE_NAME", value = var.db_name },
        { name = "DATABASE_USER", value = var.db_username }
      ],
      secrets = [
        { name = "DATABASE_PASSWORD", valueFrom = aws_ssm_parameter.db_password.arn }
      ],
      logConfiguration = {
        logDriver = "awslogs",
        options = {
          awslogs-group         = aws_cloudwatch_log_group.django.name,
          awslogs-region        = var.region,
          awslogs-stream-prefix = "cron"
        }
      },
      # EXAMPLE: call a Django management command
      command = ["python", "manage.py", "daily_job"]
    }
  ])
}

# Role that allows EventBridge Scheduler to run the ECS task and pass roles
data "aws_iam_policy_document" "scheduler_assume" {
  statement {
    actions = ["sts:AssumeRole"]
    principals { 
	  type = "Service"
	  identifiers = ["scheduler.amazonaws.com"] 
	}
  }
}

resource "aws_iam_role" "scheduler_run_ecs" {
  name               = "${var.project}-${var.env}-scheduler-ecs"
  assume_role_policy = data.aws_iam_policy_document.scheduler_assume.json
}

data "aws_iam_policy_document" "scheduler_run_ecs_doc" {
  statement {
    sid     = "RunTask"
    effect  = "Allow"
    actions = ["ecs:RunTask"]
    resources = [aws_ecs_task_definition.cron.arn]
    condition {
      test     = "StringEquals"
      variable = "ecs:cluster"
      values   = [data.terraform_remote_state.bootstrap.outputs.ecs_cluster_arn]
    }
  }

  statement {
    sid     = "PassRoles"
    effect  = "Allow"
    actions = ["iam:PassRole"]
    resources = [
      aws_iam_role.ecs_task_execution.arn,
      aws_iam_role.ecs_task.arn
    ]
  }
}

resource "aws_iam_role_policy" "scheduler_run_ecs_policy" {
  name   = "${var.project}-${var.env}-scheduler-ecs"
  role   = aws_iam_role.scheduler_run_ecs.id
  policy = data.aws_iam_policy_document.scheduler_run_ecs_doc.json
}

# EventBridge Scheduler that triggers the ECS task once per day
resource "aws_scheduler_schedule" "daily" {
  name                         = "${var.project}-${var.env}-daily-ecs"
  description                  = "Run daily Django job as ECS task"
  schedule_expression          = "cron(${var.schedule_minute} ${var.schedule_hour} * * ? *)"
  schedule_expression_timezone = var.daily_schedule_timezone

  flexible_time_window { mode = "OFF" }

  target {
    arn      = data.terraform_remote_state.bootstrap.outputs.ecs_cluster_arn
    role_arn = aws_iam_role.scheduler_run_ecs.arn

    ecs_parameters {
      task_definition_arn = aws_ecs_task_definition.cron.arn
      launch_type         = "FARGATE"
      platform_version    = "LATEST"
      network_configuration {
        assign_public_ip = false
        subnets          = data.terraform_remote_state.bootstrap.outputs.private_subnets
        security_groups  = [aws_security_group.svc.id]
      }
      task_count = 1
    }
  }
}

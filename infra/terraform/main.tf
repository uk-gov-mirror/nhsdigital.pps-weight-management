####################################################################
#
# Terraform AWS Configuration for PPS Weight Management
# -----------------------------------------------------
# 
# - Each environment has it's own terraform.tfvars variables definition file in /envs/{environment}
# - Terraform state is stored in the S3 instance created in /bootstrap/backend.tf
# 
# Run this script after each infrastructure change (example for poc environemnt)
# 
# > cd infra/terraform
# > terraform init -backend-config="bucket=nhse-pps-wm-terraform-state-bucket" -backend-config="key=poc/terraform.tfstate" -backend-config="region=eu-west-2"
# > terraform apply -auto-approve -var-file="envs/poc/terraform.tfvars"
# 
# Infrastrcuture created
# 
#                 TODO
# 
# Version History:
#
# Date       | Comment
# -----------+----------------------------------------------------
# 2025-09-05 | Initial version
# 2025-09-14 | Added Event Scheduler
# 2025-11-05 | Refactored to switch to Jinja/Django/Postgres
#
####################################################################

############################################
# Terraform and AWS Provider Configuration
############################################
# Defines the required Terraform version and providers.
# Configure the S3 backend for remote state management,
# which is crucial for collaborative development.
############################################

terraform {
  required_version = ">= 1.6"

  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
    random = {
      source  = "hashicorp/random"
      version = "~> 3.6"
    }
  }

  backend "s3" {
    bucket       = "nhse-pps-wm-terraform-state-bucket"
    use_lockfile = true
    encrypt      = true
    # key/region configured via -backend-config in init command
  }
}

############################
# Providers
############################

provider "aws" {
  region = var.region
  default_tags {
    tags = {
      Project = "${var.project}-${var.env}"
    }
  }
}

# CloudFront/WAF live in us-east-1
provider "aws" {
  alias  = "us-east-1"
  region = "us-east-1"
  default_tags {
    tags = {
      Project = "${var.project}-${var.env}"
    }
  }
}

############################
# VPC (terraform-aws-modules/vpc)
############################

module "vpc" {
  source  = "terraform-aws-modules/vpc/aws"
  version = "~> 5.0"

  name = "${var.project}-${var.env}-vpc"
  cidr = var.vpc_cidr
  azs  = var.azs

  public_subnets  = var.public_subnet_cidrs
  private_subnets = var.private_subnet_cidrs

  enable_dns_hostnames = true
  enable_dns_support   = true

  manage_default_network_acl = false
  manage_default_security_group = false

  enable_nat_gateway = true
  single_nat_gateway = true

  public_subnet_tags = {
    "kubernetes.io/role/elb" = "1"
  }

  private_subnet_tags = {
    "kubernetes.io/role/internal-elb" = "1"
  }
}

############################
# Data sources
############################

data "aws_caller_identity" "current" {}
data "aws_region" "current" {}

############################################
# ECR for Django image
############################################

resource "aws_ecr_repository" "django" {
  name                 = "${var.project}-${var.env}-django"
  force_delete = true
  image_tag_mutability = "MUTABLE"
  image_scanning_configuration { scan_on_push = true }
}

############################################
# Security groups
############################################

# CloudFront origin-facing IPv4 managed prefix list
data "aws_ec2_managed_prefix_list" "cloudfront_origin" {
  name = "com.amazonaws.global.cloudfront.origin-facing"
}

# ALB -> public 80 (switch to 443 once you add ACM/TLS on ALB)
resource "aws_security_group" "alb" {
  name        = "${var.project}-${var.env}-alb-sg"
  description = "ALB ingress"
  vpc_id      = module.vpc.vpc_id

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
  vpc_id      = module.vpc.vpc_id

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
  vpc_id      = module.vpc.vpc_id

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

############################################
# RDS PostgreSQL
############################################

resource "aws_db_subnet_group" "pg" {
  name       = "${var.project}-${var.env}-pg-subnets"
  subnet_ids = module.vpc.private_subnets
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

############################################
# ECS Fargate (Django)
############################################

resource "aws_ecs_cluster" "app" {
  name = "${var.project}-${var.env}-ecs"
}

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
      image     = "${aws_ecr_repository.django.repository_url}:${var.django_image_tag}"
      essential = true
      portMappings = [{ containerPort = var.django_container_port, hostPort = var.django_container_port, protocol = "tcp" }]
      environment = [
        { name = "DATABASE_HOST",         value = aws_db_instance.pg.address },
        { name = "DATABASE_PORT",         value = "5432" },
        { name = "DATABASE_NAME",         value = var.db_name },
        { name = "DATABASE_USER",         value = var.db_username },
		
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

# ALB + target group + listener
resource "aws_lb" "app" {
  name               = "${var.project}-${var.env}-alb"
  load_balancer_type = "application"
  internal           = false
  subnets            = module.vpc.public_subnets
  security_groups    = [aws_security_group.alb.id]
}

resource "aws_lb_target_group" "app" {
  name        = "${var.project}-${var.env}-tg"
  port        = var.django_container_port
  protocol    = "HTTP"
  vpc_id      = module.vpc.vpc_id
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

resource "aws_ecs_service" "web" {
  name            = "${var.project}-${var.env}-web"
  cluster         = aws_ecs_cluster.app.id
  task_definition = aws_ecs_task_definition.django.arn
  desired_count   = 2
  launch_type     = "FARGATE"

  network_configuration {
    assign_public_ip = false
    subnets          = module.vpc.private_subnets
    security_groups  = [aws_security_group.svc.id]
  }

  load_balancer {
    target_group_arn = aws_lb_target_group.app.arn
    container_name   = "web"
    container_port   = var.django_container_port
  }

  depends_on = [aws_lb_listener.http]
}

############################################
# CloudFront (retargeted to ALB) + WAF
############################################

resource "aws_wafv2_web_acl" "site_waf" {
  provider    = aws.us-east-1
  name        = "${var.project}-${var.env}-waf"
  description = "WAF for the website"
  scope       = "CLOUDFRONT"

  default_action { 
    allow {} 
  }

  visibility_config {
    cloudwatch_metrics_enabled = true
    metric_name                = "${var.project}-${var.env}-waf"
    sampled_requests_enabled   = true
  }

  rule {
    name     = "AWS-AWSManagedRulesCommonRuleSet"
    priority = 1
    statement {
      managed_rule_group_statement {
        vendor_name = "AWS"
        name        = "AWSManagedRulesCommonRuleSet"
      }
    }
    override_action { 
	  none {} 
	}
	
    visibility_config {
      cloudwatch_metrics_enabled = true
      metric_name                = "${var.project}-${var.env}-waf-common"
      sampled_requests_enabled   = true
    }
  }
}

resource "aws_cloudfront_distribution" "cdn" {
  provider            = aws.us-east-1
  enabled             = true
  price_class         = "PriceClass_100"
  wait_for_deployment = true
  web_acl_id          = aws_wafv2_web_acl.site_waf.arn

  origin {
    domain_name = aws_lb.app.dns_name
    origin_id   = "alb-origin"

    custom_origin_config {
      http_port              = 80
      https_port             = 443
      origin_protocol_policy = "http-only" # switch to https-only if ALB has TLS
      origin_ssl_protocols   = ["TLSv1.2"]
    }
  }

  ordered_cache_behavior {
    path_pattern     = "/secure/api/*"
    target_origin_id = "alb-origin"

    allowed_methods        = ["GET", "HEAD", "OPTIONS", "PUT", "POST", "PATCH", "DELETE"]
    cached_methods         = ["GET", "HEAD"]
    viewer_protocol_policy = "redirect-to-https"

    # Do NOT cache authenticated API responses
    min_ttl     = 0
    default_ttl = 0
    max_ttl     = 0

    forwarded_values {
      query_string = true
      headers      = ["Authorization", "Host", "Origin"]
      cookies { forward = "all" }
    }
  }

  default_cache_behavior {
    allowed_methods  = ["GET", "HEAD", "OPTIONS", "PUT", "POST", "PATCH", "DELETE"]
    cached_methods   = ["GET", "HEAD"]
    target_origin_id = "alb-origin"

    viewer_protocol_policy = "redirect-to-https"

    forwarded_values {
      query_string = true
      headers      = ["Authorization", "Host", "Origin"]
      cookies { 
	    forward = "all" 
	  }
    }
  }

  restrictions {
    geo_restriction {
      restriction_type = "none"
      locations        = []
    }
  }

  viewer_certificate {
    cloudfront_default_certificate = true
  }
}

############################################
# Cognito
############################################

resource "aws_cognito_user_pool" "up" {
  name = "${var.project}-${var.env}-users"
}

resource "aws_cognito_user_pool_client" "spa" {
  name                                 = "${var.project}-${var.env}-spa"
  user_pool_id                         = aws_cognito_user_pool.up.id
  generate_secret                      = false
  allowed_oauth_flows                  = ["code"]
  allowed_oauth_scopes                 = ["openid", "email", "profile"]
  allowed_oauth_flows_user_pool_client = true
  callback_urls                        = ["https://${aws_cloudfront_distribution.cdn.domain_name}/"]
  logout_urls                          = ["https://${aws_cloudfront_distribution.cdn.domain_name}/"]
  supported_identity_providers         = ["COGNITO"]
}


# ALB/OIDC client (confidential client, has a secret)
resource "aws_cognito_user_pool_client" "alb" {
  name         = "${var.project}-${var.env}-alb-client"
  user_pool_id = aws_cognito_user_pool.up.id

  generate_secret = true

  # OIDC config used by ALB
  allowed_oauth_flows_user_pool_client = true
  allowed_oauth_flows                  = ["code"]
  allowed_oauth_scopes                 = ["openid", "email", "profile"]
  supported_identity_providers         = ["COGNITO"]

  callback_urls = ["https://${aws_cloudfront_distribution.cdn.domain_name}/oauth2/idpresponse"]
  logout_urls = ["https://${aws_cloudfront_distribution.cdn.domain_name}"]

  prevent_user_existence_errors = "ENABLED"
}

# App client used ONLY by CI to get tokens with USER_PASSWORD_AUTH
resource "aws_cognito_user_pool_client" "ci" {
  name         = "${var.project}-${var.env}-ci"
  user_pool_id = aws_cognito_user_pool.up.id

  # No Hosted UI OAuth needed here; we want the explicit SDK auth flow.
  allowed_oauth_flows_user_pool_client = false
  generate_secret                      = false   # public client; secret not needed in CI

  # Allow the Cognito-specific password auth flow
  explicit_auth_flows = [
    "ALLOW_USER_PASSWORD_AUTH",
    "ALLOW_REFRESH_TOKEN_AUTH"
  ]

  # Token lifetimes you prefer during tests
  access_token_validity = 60
  id_token_validity     = 60
  refresh_token_validity = 30
  token_validity_units {
    access_token  = "minutes"
    id_token      = "minutes"
    refresh_token = "days"
  }
}

resource "aws_cognito_user_pool_domain" "domain" {
  domain       = "${var.project}-${var.env}-auth"
  user_pool_id = aws_cognito_user_pool.up.id
}

############################################
# GitHub OIDC 
############################################

data "aws_iam_policy_document" "gh_oidc_assume" {
  statement {
    effect = "Allow"
    actions = ["sts:AssumeRoleWithWebIdentity"]
    principals {
      type        = "Federated"
      identifiers = ["arn:aws:iam::${data.aws_caller_identity.current.account_id}:oidc-provider/token.actions.githubusercontent.com"]
    }
    condition {
      test     = "StringLike"
      variable = "token.actions.githubusercontent.com:sub"
      values = [
        "repo:${var.gh_owner}/${var.gh_repo}:ref:refs/heads/main",
        "repo:${var.gh_owner}/${var.gh_repo}:pull_request",
        "repo:${var.gh_owner}/${var.gh_repo}:environment:${var.env}"
      ]
    }
    condition {
      test     = "StringEquals"
      variable = "token.actions.githubusercontent.com:aud"
      values   = ["sts.amazonaws.com"]
    }
  }
}

resource "aws_iam_role" "gh_oidc" {
  name               = "${var.project}-${var.env}-gh-oidc"
  assume_role_policy = data.aws_iam_policy_document.gh_oidc_assume.json
}

# Build the policy document
data "aws_iam_policy_document" "deploy_policy" {
  # Broad rights in eu-west-2 and us-east-1 (covers EC2/VPC/ELB/ECR/RDS/etc.)
  statement {
    sid       = "AllowEverythingInDeploymentRegions"
    effect    = "Allow"
    actions   = ["*"]
    resources = ["*"]

    condition {
      test     = "StringEquals"
      variable = "aws:RequestedRegion"
      values   = ["eu-west-2", "us-east-1"]
    }
  }

  # Global services that don't send a region (needed for your stack)
  statement {
    sid       = "AllowGlobalServices"
    effect    = "Allow"
    actions   = [
      # CloudFront/WAF (global control plane lives behind us-east-1 endpoints)
      "cloudfront:*",
      "wafv2:*",

      # Route53 is global (hosted zones, records, health checks)
      "route53:*",

      # IAM reads + PassRole for service roles your stack uses
      "iam:Get*",
      "iam:List*",
      "iam:PassRole",

      # Handy diagnostics for failed auth messages
      "sts:DecodeAuthorizationMessage"
    ]
    resources = ["*"]
  }
}

resource "aws_iam_policy" "deploy_policy" {
  name        = "${var.project}-${var.env}-deploy-policy"
  description = "Broad CI policy limited to eu-west-2 & us-east-1 plus required global services"
  policy      = data.aws_iam_policy_document.deploy_policy.json
}

resource "aws_iam_role_policy_attachment" "attach_deploy_policy" {
  role       = aws_iam_role.gh_oidc.name
  policy_arn = aws_iam_policy.deploy_policy.arn
}

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
      image     = "${aws_ecr_repository.django.repository_url}:${var.django_image_tag}",
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
      values   = [aws_ecs_cluster.app.arn]
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
    arn      = aws_ecs_cluster.app.arn
    role_arn = aws_iam_role.scheduler_run_ecs.arn

    ecs_parameters {
      task_definition_arn = aws_ecs_task_definition.cron.arn
      launch_type         = "FARGATE"
      platform_version    = "LATEST"
      network_configuration {
        assign_public_ip = false
        subnets          = module.vpc.private_subnets
        security_groups  = [aws_security_group.svc.id]
      }
      task_count = 1
    }
  }
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

resource "aws_ssm_parameter" "cognito_client_id" {
  name        = "/${var.project}/${var.env}/cognito/client_id"
  description = "Cognito App Client ID"
  type        = "String"
  value       = aws_cognito_user_pool_client.ci.id
  overwrite   = true
  tags = {
    Project = var.project
    Env     = var.env
  }
}

resource "aws_ssm_parameter" "cognito_user_pool_id" {
  name        = "/${var.project}/${var.env}/cognito/user_pool_id"
  description = "Cognito User Pool ID"
  type        = "String"
  value       = aws_cognito_user_pool.up.id
  overwrite   = true
  tags = {
    Project = var.project
    Env     = var.env
  }
}

resource "aws_ssm_parameter" "aws_region" {
  name        = "/${var.project}/${var.env}/region"
  description = "AWS region for this deployment"
  type        = "String"
  value       = var.region
  overwrite   = true
  tags = {
    Project = var.project
    Env     = var.env
  }
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

# --- SSM bastion SG (no inbound, all outbound) ---
resource "aws_security_group" "ssm_bastion" {
  name   = "${var.project}-${var.env}-ssm-bastion-sg"
  vpc_id = module.vpc.vpc_id

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

# --- IAM role/profile for SSM on the EC2 instance ---
data "aws_iam_policy_document" "bastion_assume" {
  statement {
    actions = ["sts:AssumeRole"]
    principals {
      type        = "Service"
      identifiers = ["ec2.amazonaws.com"]
    }
  }
}

resource "aws_iam_role" "bastion_role" {
  name               = "${var.project}-${var.env}-ssm-bastion-role"
  assume_role_policy = data.aws_iam_policy_document.bastion_assume.json
}

resource "aws_iam_role_policy_attachment" "bastion_ssm_core" {
  role       = aws_iam_role.bastion_role.name
  policy_arn = "arn:aws:iam::aws:policy/AmazonSSMManagedInstanceCore"
}

resource "aws_iam_instance_profile" "bastion_profile" {
  name = "${var.project}-${var.env}-ssm-bastion-profile"
  role = aws_iam_role.bastion_role.name
}

# --- Amazon Linux 2023 AMI (has SSM Agent) ---
data "aws_ami" "al2023" {
  most_recent = true
  owners      = ["amazon"]
  filter {
    name   = "name"
    values = ["al2023-ami-*-x86_64"]
  }
}

# --- EC2 bastion in a PRIVATE subnet (no public IP) ---
resource "aws_instance" "ssm_bastion" {
  ami                         = data.aws_ami.al2023.id
  instance_type               = "t3.nano"
  subnet_id                   = module.vpc.private_subnets[0]
  associate_public_ip_address = false
  iam_instance_profile        = aws_iam_instance_profile.bastion_profile.name
  vpc_security_group_ids      = [aws_security_group.ssm_bastion.id]

  tags = { Name = "${var.project}-${var.env}-ssm-bastion" }
}

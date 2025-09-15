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
#               +--------------------------+
#               |    AWS WAFv2 Web ACL     |
#               |   (Global Protection)    |
#               +------------+-------------+
#                            |
#                            v
# +----------------------------------------------------------------+
# |            AWS CloudFront (CDN Distribution)                   |
# |                                                                |
# |  +------------------+ +--------------------------------------+ |
# |  |  Static Content  | |          API Requests                | |
# |  |   (path: /*)     | | (paths: /public/api/*,/secure/api/*) | |
# |  +------------------+ +--------------------------------------+ |
# |           |                            |                       |
# +----------------------------------------------------------------+
#             |                            |
#             v                            v
#    +----------------+           +-----------------+
#    |  S3 Bucket     |           |   API Gateway   |
#    | (Static Site)  |           |   (HTTP API)    |
#    +----------------+           +-----------------+
#                                          |
#                                          |
#                          +---------------+-------------+
#                          |  Public API   | Secure API  |
#                          |  (No Auth)    | (JWT Auth)  |
#                          +---------------+-------------+
#                                  |       |   Cognito   |
#   +------------------+           |       |  User Pool  |
#   | Event Scheduler  |           |       +-------------+
#   |                  |           |             |
#   +--------+---------+           +-------------+
#            |                             |
#            v                             v
#   +--------+---------+         +------------------+
#   |    AWS Lambda    |         |    AWS Lambda    |
#   |    (Daily Job)   |         |   (API Backend)  |
#   +------------------+         +--------+---------+
#                                         |
#                                         v
#                                +------------------+
#                                |  AWS DynamoDB    |
#                                | (Data Storage)   |
#                                +------------------+
# 
# Version History:
#
# Date       | Comment
# -----------+----------------------------------------------------
# 2025-09-05 | Initial version
# 2025-09-14 | Added Event Scheduler
#
####################################################################

############################################
# Terraform and AWS Provider Configuration
############################################
# Defines the required Terraform version and providers.
# Configure the S3 backend for remote state management,
# which is crucial for collaborative development.
# Relates to: Terraform, S3, DynamoDB (via use_lockfile)
terraform {
  required_version = ">= 1.6"
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }

  backend "s3" {
    bucket         = "nhse-pps-wm-terraform-state-bucket"
    use_lockfile   = true
    encrypt        = true
  }
}

# Configures the primary AWS provider for the main region.
# This provider is used for all resources not explicitly tied to a different region.
# Relates to: AWS
provider "aws" {
  region = var.region
  # This block will automatically apply the 'Project' tag to all supported resources.
  default_tags {
    tags = {
      Project = "${var.project}-${var.env}"
    }
  }
}

# Configures a second AWS provider for the `us-east-1` region.
# This is a requirement for CloudFront and WAF resources.
# Relates to: AWS, CloudFront, WAF
provider "aws" {
  alias  = "us-east-1"
  region = "us-east-1"
  # This block will automatically apply the 'Project' tag to all supported resources.
  default_tags {
    tags = {
      Project = "${var.project}-${var.env}"
    }
  }
}

############################################
# Data Sources
############################################
# Fetches the account ID of the current AWS user.
# Relates to: AWS
data "aws_caller_identity" "current" {}

# Fetches the name of the current AWS region.
# Relates to: AWS
data "aws_region" "current" {}

# Fetches a managed CloudFront policy that forwards all viewer request
# headers, cookies, and query strings to the origin, except for the
# `Host` header. This is a best practice for API integrations.
# Relates to: CloudFront, API Gateway
data "aws_cloudfront_origin_request_policy" "managed_all_viewer_except_host_header" {
  name = "Managed-AllViewerExceptHostHeader"
}

############################################
# S3 Site Bucket
############################################
# The S3 bucket that hosts the static website files. It's configured to be
# completely private, with access only allowed via CloudFront.
# Relates to: S3, CloudFront
resource "aws_s3_bucket" "site" {
  bucket        = "${var.project}-${var.env}-site"
  force_destroy = true
}

# Prevents public access to the S3 bucket, ensuring it can only be accessed
# through the CloudFront distribution.
# Relates to: S3
resource "aws_s3_bucket_public_access_block" "site" {
  bucket = aws_s3_bucket.site.id

  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

# Enables versioning for the S3 bucket, providing a way to recover
# from accidental deletions or overwrites.
# Relates to: S3
resource "aws_s3_bucket_versioning" "site" {
  bucket = aws_s3_bucket.site.id

  versioning_configuration {
    status = "Enabled"
  }
}

# Creates an Origin Access Control (OAC) to secure the connection
# between CloudFront and the S3 bucket, ensuring only CloudFront can
# access the files.
# Relates to: CloudFront, S3
resource "aws_cloudfront_origin_access_control" "oac" {
  name                              = "${var.project}-${var.env}-oac"
  origin_access_control_origin_type = "s3"
  signing_behavior                  = "always"
  signing_protocol                  = "sigv4"
}

# Defines the IAM policy document that grants CloudFront permission to read
# objects from the S3 bucket via the OAC.
# Relates to: S3, IAM, CloudFront
data "aws_iam_policy_document" "site_policy" {
  statement {
    actions   = ["s3:GetObject"]
    resources = ["${aws_s3_bucket.site.arn}/*"]

    principals {
      type        = "Service"
      identifiers = ["cloudfront.amazonaws.com"]
    }

    condition {
      test     = "StringEquals"
      variable = "AWS:SourceArn"
      values   = [aws_cloudfront_distribution.cdn.arn]
    }
  }
}

# Attaches the policy to the S3 bucket, granting CloudFront read access.
# Relates to: S3, IAM
resource "aws_s3_bucket_policy" "site" {
  bucket = aws_s3_bucket.site.id
  policy = data.aws_iam_policy_document.site_policy.json
}

############################################
# WAF (Web Application Firewall)
############################################
# Creates a Web Application Firewall (WAF) to protect the website. This WAF
# includes a common rule set to protect against attacks like
# cross-site scripting (XSS) and SQL injection.
# Relates to: WAF, CloudFront
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
    name     = "AWS-Managed-CoreRuleSet"
    priority = 1

    override_action {
      none {}
    }

    statement {
      managed_rule_group_statement {
        vendor_name = "AWS"
        name        = "AWSManagedRulesCommonRuleSet"
      }
    }

    visibility_config {
      cloudwatch_metrics_enabled = true
      metric_name                = "AWSManagedRulesCommonRuleSet"
      sampled_requests_enabled   = true
    }
  }

  rule {
    name     = "AWS-Managed-SQLi"
    priority = 2

    override_action {
      none {}
    }

    statement {
      managed_rule_group_statement {
        vendor_name = "AWS"
        name        = "AWSManagedRulesSQLiRuleSet"
      }
    }

    visibility_config {
      cloudwatch_metrics_enabled = true
      metric_name                = "AWSManagedRulesSQLiRuleSet"
      sampled_requests_enabled   = true
    }
  }
}

############################################
# CloudFront Distribution
############################################
# Generates a random string that is used as a shared secret between
# CloudFront and the API Gateway origin. This prevents direct access to the
# API Gateway from anywhere but the CloudFront distribution.
# Relates to: CloudFront, API Gateway, Lambda
resource "random_string" "origin_secret" {
  length  = 32
  upper   = false
  numeric = true
  special = false
}

resource "aws_ssm_parameter" "origin_secret" {
  name  = "/${var.project}/${var.env}/origin-secret"
  type  = "SecureString"
  value = random_string.origin_secret.result
}

# Deploys the static web assets and API. This is the public-facing
# entry point, providing caching, security (via the WAF), and SSL/TLS.
# Relates to: CloudFront, S3, API Gateway, WAF
resource "aws_cloudfront_distribution" "cdn" {
  enabled             = true
  price_class         = "PriceClass_100"
  default_root_object = "index.html"
  wait_for_deployment = true
  web_acl_id          = aws_wafv2_web_acl.site_waf.arn

  # S3 origin (site)
  origin {
    domain_name              = aws_s3_bucket.site.bucket_regional_domain_name
    origin_id                = "s3-site"
    origin_access_control_id = aws_cloudfront_origin_access_control.oac.id
  }

  # API origin (API Gateway)
  origin {
    domain_name = replace(replace(aws_apigatewayv2_api.http_api.api_endpoint, "https://", ""), "http://", "")
    origin_id   = "api-origin"

    # Custom header used by WAF to allow only CloudFront
    custom_header {
      name  = "X-Origin-Secret"
      value = random_string.origin_secret.result
    }

    custom_origin_config {
      http_port              = 80
      https_port             = 443
      origin_protocol_policy = "https-only"
      origin_ssl_protocols   = ["TLSv1.2"]
    }
  }

  # Default behavior: static site
  default_cache_behavior {
    target_origin_id       = "s3-site"
    viewer_protocol_policy = "redirect-to-https"
    allowed_methods        = ["GET", "HEAD"]
    cached_methods         = ["GET", "HEAD"]
    cache_policy_id        = "658327ea-f89d-4fab-a63d-7e88639e58f6" # AWS: CachingOptimized
    compress               = true
  }

  # Public API (no caching, don't forward Host)
  ordered_cache_behavior {
    path_pattern             = "/public/api/*"
    target_origin_id         = "api-origin"
    viewer_protocol_policy   = "https-only"
    allowed_methods          = ["GET", "HEAD", "OPTIONS", "PUT", "POST", "PATCH", "DELETE"]
    cached_methods           = ["GET", "HEAD", "OPTIONS"]
    cache_policy_id          = "4135ea2d-6df8-44a3-9df3-4b5a84be39ad"
    origin_request_policy_id = data.aws_cloudfront_origin_request_policy.managed_all_viewer_except_host_header.id
  }

  ordered_cache_behavior {
    path_pattern             = "/secure/api/*"
    target_origin_id         = "api-origin"
    viewer_protocol_policy   = "https-only"
    allowed_methods          = ["GET", "HEAD", "OPTIONS", "PUT", "POST", "PATCH", "DELETE"]
    cached_methods           = ["GET", "HEAD", "OPTIONS"]
    cache_policy_id          = "4135ea2d-6df8-44a3-9df3-4b5a84be39ad"
    origin_request_policy_id = data.aws_cloudfront_origin_request_policy.managed_all_viewer_except_host_header.id
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
# DynamoDB Table
############################################
# Creates the DynamoDB table for the API to store data. It's configured
# for on-demand billing and includes point-in-time recovery for backup.
# Relates to: DynamoDB, Lambda
resource "aws_dynamodb_table" "items" {
  name         = "${var.project}-${var.env}-items"
  billing_mode = "PAY_PER_REQUEST"
  hash_key     = "pk"
  range_key    = "sk"

  attribute {
    name = "pk"
    type = "S"
  }

  attribute {
    name = "sk"
    type = "S"
  }

  point_in_time_recovery {
    enabled = true
  }

  server_side_encryption {
    enabled = true
  }
}

############################################
# Lambda Function and IAM Role
############################################
# Defines the trust policy that allows the Lambda service to assume the role.
# This is a prerequisite for a Lambda function to be able to use the role's
# permissions.
# Relates to: IAM, Lambda
data "aws_iam_policy_document" "lambda_assume" {
  statement {
    actions = ["sts:AssumeRole"]

    principals {
      type        = "Service"
      identifiers = ["lambda.amazonaws.com"]
    }
  }
}

# Creates the IAM role for the Lambda function, which defines the permissions
# that the function will have.
# Relates to: IAM, Lambda
resource "aws_iam_role" "lambda" {
  name               = "${var.project}-${var.env}-lambda-role"
  assume_role_policy = data.aws_iam_policy_document.lambda_assume.json
}

# Defines the IAM policy document that grants the Lambda function read/write
# access to the DynamoDB table.
# Relates to: IAM, DynamoDB, Lambda
data "aws_iam_policy_document" "lambda_ddb" {
  statement {
    actions = [
      "dynamodb:GetItem",
      "dynamodb:PutItem",
      "dynamodb:UpdateItem",
      "dynamodb:Query",
      "dynamodb:DeleteItem"
    ]
    resources = [
      aws_dynamodb_table.items.arn,
      "${aws_dynamodb_table.items.arn}/index/*"
    ]
  }
}

# Creates the DynamoDB access policy from the policy document.
# Relates to: IAM, DynamoDB
resource "aws_iam_policy" "ddb" {
  name   = "${var.project}-${var.env}-ddb-policy"
  policy = data.aws_iam_policy_document.lambda_ddb.json
}

# Attaches the DynamoDB policy to the Lambda IAM role.
# Relates to: IAM, DynamoDB
resource "aws_iam_role_policy_attachment" "ddb_attach" {
  role       = aws_iam_role.lambda.name
  policy_arn = aws_iam_policy.ddb.arn
}

# Attaches the AWS-managed basic execution role policy to the Lambda IAM role,
# which allows the function to write logs to CloudWatch.
# Relates to: IAM, Lambda, CloudWatch Logs
resource "aws_iam_role_policy_attachment" "logs_attach" {
  role       = aws_iam_role.lambda.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole"
}

locals {
  api_zip = abspath(
    var.api_zip_path != "" ? var.api_zip_path : "${path.module}/../../api.zip"
  )

  # Safe for destroy: if the file isn't present, return null
  api_zip_hash = fileexists(local.api_zip) ? filebase64sha256(local.api_zip) : null
}

# Creates a CloudWatch log group for the REST API logs.
resource "aws_cloudwatch_log_group" "api" {
  name              = "/aws/lambda/${var.project}-${var.env}-api"
  retention_in_days = 14
}

# Lambda function for REST API
resource "aws_lambda_function" "api" {
  function_name = "${var.project}-${var.env}-api"
  role          = aws_iam_role.lambda.arn
  handler       = "handler.handler"
  runtime       = "nodejs20.x"

  filename         = local.api_zip
  source_code_hash = local.api_zip_hash

  environment {
    variables = {
      TABLE_NAME    = aws_dynamodb_table.items.name
      ORIGIN_SECRET = random_string.origin_secret.result
    }
  }

  timeout = 10
}

############################################
# Cognito User Pool
############################################
# Creates a Cognito User Pool for user authentication and management.
# Relates to: Cognito, API Gateway
resource "aws_cognito_user_pool" "up" {
  name = "${var.project}-${var.env}-users"
}

# Creates a client for the user pool, allowing single-page applications (SPA)
# to authenticate with the user pool.
# Relates to: Cognito
resource "aws_cognito_user_pool_client" "spa" {
  name                                 = "${var.project}-${var.env}-spa"
  user_pool_id                         = aws_cognito_user_pool.up.id
  generate_secret                      = false
  allowed_oauth_flows                  = ["code"]
  allowed_oauth_scopes                 = ["openid", "email", "profile"]
  allowed_oauth_flows_user_pool_client = true
  callback_urls                        = ["https://example.com/callback"] # TODO: Change this
  logout_urls                          = ["https://example.com"]          # TODO: Change this
  supported_identity_providers         = ["COGNITO"]
}

# Creates a domain for the Cognito user pool, which is needed for the
# hosted UI and JWT issuer URL.
# Relates to: Cognito
resource "aws_cognito_user_pool_domain" "domain" {
  domain       = "${var.project}-${var.env}-auth"
  user_pool_id = aws_cognito_user_pool.up.id
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

############################################
# API Gateway
############################################
# Creates the API Gateway HTTP API, which acts as a front door for the
# Lambda function. It handles routing requests and manages security.
# Relates to: API Gateway, Lambda, Cognito
resource "aws_apigatewayv2_api" "http_api" {
  name          = "${var.project}-${var.env}-http"
  protocol_type = "HTTP"

  cors_configuration {
    allow_origins = ["*"]
    allow_methods = ["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"]
    allow_headers = ["*"]
  }
}

# Creates a new API Gateway integration that links the API with the Lambda function.
# Relates to: API Gateway, Lambda
resource "aws_apigatewayv2_integration" "lambda_proxy" {
  api_id                 = aws_apigatewayv2_api.http_api.id
  integration_type       = "AWS_PROXY"
  integration_uri        = aws_lambda_function.api.arn
  payload_format_version = "2.0"
}

# Grants API Gateway permission to invoke the Lambda function.
# Relates to: API Gateway, Lambda
resource "aws_lambda_permission" "apigw_invoke" {
  statement_id  = "AllowInvokeFromAPIGW"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.api.function_name
  principal     = "apigateway.amazonaws.com"
  source_arn    = "${aws_apigatewayv2_api.http_api.execution_arn}/*/*"
}

# Creates a JWT authorizer for the API Gateway, which uses Cognito
# to authenticate and authorize requests to secure paths.
# Relates to: API Gateway, Cognito
resource "aws_apigatewayv2_authorizer" "jwt" {
  api_id           = aws_apigatewayv2_api.http_api.id
  name             = "cognito-jwt"
  authorizer_type  = "JWT"
  identity_sources = ["$request.header.Authorization"]

  jwt_configuration {
    issuer   = "https://cognito-idp.${data.aws_region.current.name}.amazonaws.com/${aws_cognito_user_pool.up.id}"
    audience = [
      aws_cognito_user_pool_client.spa.id,  # browser client
      aws_cognito_user_pool_client.ci.id    # CI client (USER_PASSWORD_AUTH)
    ]
  }
}

# Defines the API route for public (unauthenticated) requests.
# Relates to: API Gateway
resource "aws_apigatewayv2_route" "public_ping" {
  api_id             = aws_apigatewayv2_api.http_api.id
  route_key          = "GET /public/api/ping"
  target             = "integrations/${aws_apigatewayv2_integration.lambda_proxy.id}"
  authorization_type = "NONE"
  authorizer_id      = null
}

# Defines a catch-all API route for public (unauthenticated) requests.
# Relates to: API Gateway
resource "aws_apigatewayv2_route" "public_proxy" {
  api_id             = aws_apigatewayv2_api.http_api.id
  route_key          = "ANY /public/api/{proxy+}"
  target             = "integrations/${aws_apigatewayv2_integration.lambda_proxy.id}"
  authorization_type = "NONE"
  authorizer_id      = null
}

# Defines a catch-all API route for secure (authenticated) requests.
# It is linked to the JWT authorizer for security.
# Relates to: API Gateway, Cognito
resource "aws_apigatewayv2_route" "secured_proxy" {
  api_id             = aws_apigatewayv2_api.http_api.id
  route_key          = "ANY /secure/api/{proxy+}"
  target             = "integrations/${aws_apigatewayv2_integration.lambda_proxy.id}"
  authorization_type = "JWT"
  authorizer_id      = aws_apigatewayv2_authorizer.jwt.id
}

# Creates a CloudWatch log group for the API Gateway access logs.
# Relates to: API Gateway, CloudWatch
resource "aws_cloudwatch_log_group" "apigateway" {
  name              = "/aws/apigateway/${var.project}-${var.env}-apigateway"
  retention_in_days = 14
}

# Creates the default API Gateway stage, which automatically deploys the API.
# It also configures detailed access logging for monitoring.
# Relates to: API Gateway, CloudWatch
resource "aws_apigatewayv2_stage" "default" {
  api_id      = aws_apigatewayv2_api.http_api.id
  name        = "$default"
  auto_deploy = true

  access_log_settings {
    destination_arn = aws_cloudwatch_log_group.apigateway.arn
    format = jsonencode({
      requestId               = "$context.requestId"
      ip                      = "$context.identity.sourceIp"
      requestTime             = "$context.requestTime"
      httpMethod              = "$context.httpMethod"
      path                    = "$context.path"
      status                  = "$context.status"
      protocol                = "$context.protocol"
      responseLength          = "$context.responseLength"
      authorizerStatus        = "$context.authorizer.status"
      authorizerError         = "$context.authorizer.error"
      integrationStatus       = "$context.integration.status"
      integrationErrorMessage = "$context.integration.error"
    })
  }

  default_route_settings {
    detailed_metrics_enabled = true
    throttling_burst_limit   = 5000
    throttling_rate_limit    = 10000
    logging_level            = "INFO"
    data_trace_enabled       = true
  }
}

############################################
# IAM Role for GitHub Actions OIDC
############################################
# Configures the IAM OpenID Connect (OIDC) provider for GitHub Actions.
# This is the identity provider that GitHub will use to authenticate with AWS.
# Relates to: IAM, GitHub Actions

# resource "aws_iam_openid_connect_provider" "github" {...} is created in a bootsrap script as it is only created once per AWS Account
# It is referenced here

# Defines the IAM trust policy that allows GitHub's OIDC provider to assume the role.
# This policy securely delegates permissions to GitHub Actions without
# using long-lived credentials.
# Relates to: IAM, GitHub Actions
data "aws_iam_policy_document" "oidc_trust" {
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

# The IAM role with the assume role policy (the trust policy) for GitHub Actions.
# Relates to: IAM, GitHub Actions
resource "aws_iam_role" "gh_oidc" {
  name               = "${var.project}-${var.env}-github-oidc"
  assume_role_policy = data.aws_iam_policy_document.oidc_trust.json
}

# The IAM policy that grants the required permissions to the role for deployment.
# Relates to: IAM, GitHub Actions
resource "aws_iam_policy" "deploy_policy" {
  name = "${var.project}-${var.env}-github-oidc-policy"
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "s3:*",
          "cloudfront:*",
          "route53:*",
          "lambda:*",
          "dynamodb:*",
          "cognito-idp:*",
          "cognito-identity:*",
          "wafv2:*",
          "logs:*",
          "logs:ListTagsForResource",
          "logs:DescribeLogGroups",
		  "apigateway:TagResource",
          "apigateway:GET",
          "apigateway:PATCH",
		  "apigateway:DELETE",
		  "apigateway:POST",
          "iam:GetPolicyVersion",
          "iam:GetOpenIDConnectProvider",
          "iam:PassRole",
          "iam:CreatePolicy",
          "iam:AttachRolePolicy",
          "iam:ListRolePolicies",
          "iam:ListAttachedRolePolicies",
          "iam:GetPolicy",
          "iam:PutRolePolicy",
          "iam:CreatePolicy",
          "iam:UpdateAssumeRolePolicy",
          "iam:DeleteRolePolicy",
          "iam:DeleteRole",
          "iam:DetachRolePolicy",
          "iam:GetRole",
          "iam:TagPolicy",
		  "iam:DeletePolicyVersion",
		  "iam:CreateRole",
		  "iam:CreateOpenIDConnectProvider",
		  "iam:ListPolicyVersions",
		  "iam:TagRole",
		  "iam:TagOpenIDConnectProvider",
		  "iam:CreatePolicyVersion",
		  "iam:ListOpenIDConnectProviders",
		  "iam:ListInstanceProfilesForRole",
		  "iam:GetRolePolicy",
		  "iam:DeletePolicy",
		  "scheduler:GetSchedule",
		  "scheduler:CreateSchedule",
		  "scheduler:DeleteSchedule",
		  "ssm:AddTagsToResource",
		  "ssm:GetParameters",
		  "ssm:DeleteParameter",
		  "ssm:GetParameter",
		  "ssm:DescribeParameters",
		  "ssm:ListTagsForResource",
		  "ssm:PutParameter"
        ]
        Resource = "*"
      },
    ]
  })
}

# Attaches the deployment policy to the GitHub Actions IAM role.
# Relates to: IAM, GitHub Actions
resource "aws_iam_role_policy_attachment" "attach_deploy_policy" {
  role       = aws_iam_role.gh_oidc.name
  policy_arn = aws_iam_policy.deploy_policy.arn
}

###############################################################################
# Daily scheduled Lambda (timezone-aware via EventBridge Scheduler)
# - Runs every day at HH:MM
###############################################################################
# Creates a lambda function and an EventBridge Scheduler to trigger it on a schedule
# Relates to: EventBridge Scheduler, Lambda

locals {
  daily_zip = abspath(
    var.daily_zip_path != "" ? var.daily_zip_path : "${path.module}/../../daily.zip"
  )

  # Safe for destroy: if the file isn't present, return null
  daily_zip_hash = fileexists(local.daily_zip) ? filebase64sha256(local.daily_zip) : null
}

# Lambda function for daily job
resource "aws_lambda_function" "daily" {
  function_name = "${var.project}-${var.env}-daily-job"
  role          = aws_iam_role.lambda.arn

  runtime = "nodejs20.x"
  handler = "daily.handler"

  filename         = local.daily_zip  
  source_code_hash = local.daily_zip_hash

  environment {
    variables = {
      PROJECT = var.project
      ENV     = var.env
    }
  }
}

# Explicit log group for daily job
resource "aws_cloudwatch_log_group" "daily" {
  name              = "/aws/lambda/${aws_lambda_function.daily.function_name}"
  retention_in_days = 14
}

# Scheduler role that can invoke the daily Lambda
resource "aws_iam_role" "scheduler_invoke_daily" {
  name = "${var.project}-${var.env}-scheduler-invoke-daily"
  assume_role_policy = jsonencode({
    Version = "2012-10-17",
    Statement = [{
      Effect    = "Allow",
      Principal = { Service = "scheduler.amazonaws.com" },
      Action    = "sts:AssumeRole"
    }]
  })
}

# Scheduler role policy using the scheduler role that can invoke the daily Lambda
resource "aws_iam_role_policy" "scheduler_invoke_daily" {
  name = "${var.project}-${var.env}-scheduler-invoke-daily-policy"
  role = aws_iam_role.scheduler_invoke_daily.id
  policy = jsonencode({
    Version = "2012-10-17",
    Statement = [{
      Effect   = "Allow",
      Action   = "lambda:InvokeFunction",
      Resource = aws_lambda_function.daily.arn
    }]
  })
}

# Daily schedule timezone
variable "daily_schedule_timezone" {
  description = "IANA timezone for the daily schedule (DST handled)"
  type        = string
  default     = "Europe/London"
}

# EventBridge Scheduler to run the daily job run at a fixed local time every day
resource "aws_scheduler_schedule" "daily" {
  name                         = "${var.project}-${var.env}-daily-schedule"
  description                  = "Run daily job once per day at a fixed local time"
  schedule_expression          = "cron(${var.schedule_minute} ${var.schedule_hour} * * ? *)"
  schedule_expression_timezone = var.daily_schedule_timezone

  flexible_time_window { mode = "OFF" }

  target {
    arn      = aws_lambda_function.daily.arn
    role_arn = aws_iam_role.scheduler_invoke_daily.arn
    input    = jsonencode({ run = "daily", project = var.project, env = var.env })

    # Reasonable retry defaults; tune as needed
    retry_policy {
      maximum_event_age_in_seconds = 3600
      maximum_retry_attempts       = 3
    }
  }
}

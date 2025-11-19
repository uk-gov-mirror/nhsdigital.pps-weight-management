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
# SSM Parameters for Cognito
############################################

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

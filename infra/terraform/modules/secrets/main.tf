resource "random_password" "db_password" {
  length  = 16
  special = true
}

resource "random_password" "cloudfront_custom_header" {
  length  = 32
  special = false
}

module "secrets_manager" {
  source  = "terraform-aws-modules/secrets-manager/aws"
  version = "~> 1.0"

  name                    = "${var.name}-secrets-manager"
  description             = "Secrets for ${var.name}"
  recovery_window_in_days = var.recovery_window

  # DB password secret
  secret_string = jsonencode({
    db_password              = random_password.db_password.result
    django_secret_key        = var.django_secret_key
    cloudfront_custom_header = random_password.cloudfront_custom_header.result
  })

  tags = var.tags
}
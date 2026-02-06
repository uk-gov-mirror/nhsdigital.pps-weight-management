locals {
  project        = "pps-htsh"
  environment    = "poc"
  context_string = "${local.project}-${local.environment}"
}

module "secrets" {
  source = "../../../modules/secrets"

  name              = local.context_string
  django_secret_key = ""

  tags = {
    Project     = local.project
    Environment = local.environment
  }
}

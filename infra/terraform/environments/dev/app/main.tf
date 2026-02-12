locals {
  project            = "pps-htsh"
  environment        = var.environment
  environment_suffix = var.environment_suffix
  context_string     = "${local.project}-${local.environment}-${local.environment_suffix}"
}

module "alb" {
  source = "../../../modules/alb"

  name              = local.context_string
  vpc_id            = data.aws_vpc.network.id
  public_subnet_ids = data.aws_subnets.public.ids
  alb_sg_id         = data.aws_security_group.alb.id

  tags = {
    Project     = local.project
    Environment = local.environment
    Suffix      = local.environment_suffix
  }
}

module "waf_cloudfront" {
  source = "../../../modules/waf"
  name   = "${local.context_string}-cloudfront-waf"
  scope  = "CLOUDFRONT"

  admin_ip_set_arn = data.aws_wafv2_ip_set.admin_ipset.arn

  providers = {
    aws = aws.us_east_1
  }

  tags = {
    Project     = local.project
    Environment = local.environment
    Suffix      = local.environment_suffix
  }
}

module "cloudfront" {
  source = "../../../modules/cloudfront"

  name                      = local.context_string
  alb_dns_name              = module.alb.lb_dns_name
  custom_header_value       = jsondecode(data.aws_secretsmanager_secret_version.secrets.secret_string)["cloudfront_custom_header"]
  web_acl_id                = module.waf_cloudfront.arn
  price_class               = "PriceClass_100"
  default_ttl               = 3600
  max_ttl                   = 86400
  geo_restriction_locations = ["GB"]

  aliases             = ["${local.environment_suffix}.help-to-stay-healthy-pilot.service.nhs.uk"]
  acm_certificate_arn = "arn:aws:acm:us-east-1:515424599516:certificate/d88579b2-774c-4ae8-aa4e-b1b0e0cbf609"

  # Don't cache admin or API paths
  ordered_cache_behaviors = [
    {
      path_pattern         = "/admin/*"
      allowed_methods      = ["DELETE", "GET", "HEAD", "OPTIONS", "PATCH", "POST", "PUT"]
      cached_methods       = ["GET", "HEAD"]
      forward_query_string = true
      forward_headers      = ["*"]
      forward_cookies      = "all"
      min_ttl              = 0
      default_ttl          = 0
      max_ttl              = 0
    },
    {
      path_pattern         = "/api/*"
      allowed_methods      = ["DELETE", "GET", "HEAD", "OPTIONS", "PATCH", "POST", "PUT"]
      cached_methods       = ["GET", "HEAD"]
      forward_query_string = true
      forward_headers      = ["*"]
      forward_cookies      = "all"
      min_ttl              = 0
      default_ttl          = 0
      max_ttl              = 0
    }
  ]

  tags = {
    Project     = local.project
    Environment = local.environment
    Suffix      = local.environment_suffix
  }
}

resource "aws_route53_record" "app_a" {
  zone_id = data.aws_route53_zone.main.zone_id
  name    = "${local.environment_suffix}.help-to-stay-healthy-pilot.service.nhs.uk"
  type    = "A"

  alias {
    name                   = module.cloudfront.domain_name
    zone_id                = module.cloudfront.hosted_zone_id
    evaluate_target_health = false
  }
}

resource "aws_route53_record" "app_aaaa" {
  zone_id = data.aws_route53_zone.main.zone_id
  name    = "${local.environment_suffix}.help-to-stay-healthy-pilot.service.nhs.uk"
  type    = "AAAA"

  alias {
    name                   = module.cloudfront.domain_name
    zone_id                = module.cloudfront.hosted_zone_id
    evaluate_target_health = false
  }
}

module "ecs" {
  source = "../../../modules/ecs"

  name                   = local.context_string
  docker_image           = "515424599516.dkr.ecr.eu-west-2.amazonaws.com/pps-htsh-poc-ecr"
  image_tag              = var.image_tag
  db_username            = "ppswmuser"
  db_password            = "${data.aws_db_instance.datastore.master_user_secret[0].secret_arn}:password::"
  db_endpoint            = data.aws_db_instance.datastore.endpoint
  db_name                = data.aws_db_instance.datastore.db_name
  db_address             = data.aws_db_instance.datastore.address
  service_api_base_url   = "http://${module.alb.lb_dns_name}"
  django_secret_key      = "${data.aws_secretsmanager_secret_version.secrets.arn}:django_secret_key::"
  region                 = "eu-west-2"
  private_ecs_subnet_ids = data.aws_subnets.private_ecs.ids
  ecs_sg_id              = data.aws_security_group.ecs.id
  target_group_arn       = module.alb.target_group_arns["ecs"]
  desired_count          = 1

  tags = {
    Project     = local.project
    Environment = local.environment
    Suffix      = local.environment_suffix
  }
}
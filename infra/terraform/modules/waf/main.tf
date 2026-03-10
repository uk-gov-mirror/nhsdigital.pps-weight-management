resource "aws_wafv2_web_acl" "main" {
  name        = var.name
  description = "WAFv2 Web ACL for ${var.name}"
  scope       = var.scope

  default_action {
    allow {}
  }

  dynamic "rule" {
    for_each = var.admin_ip_set_arn != null ? [1] : []

    content {
      name     = "restrict-admin-access"
      priority = 0

      action {
        block {}
      }

      statement {
        and_statement {
          statement {
            byte_match_statement {
              search_string = "/admin/"
              # search_string = "/admin/"
              field_to_match {
                uri_path {}
              }
              text_transformation {
                priority = 0
                type     = "NONE"
              }
              positional_constraint = "STARTS_WITH"
            }
          }
          statement {
            not_statement {
              statement {
                ip_set_reference_statement {
                  arn = var.admin_ip_set_arn
                }
              }
            }
          }
        }
      }

      visibility_config {
        cloudwatch_metrics_enabled = true
        metric_name                = "restrict-admin-access"
        sampled_requests_enabled   = true
      }
    }
  }

  # Rule: AWS Managed Core Rule Set
  rule {
    name     = "AWS-AWSManagedRulesCommonRuleSet"
    priority = 10
    override_action {
      none {}
    }
    statement {
      managed_rule_group_statement {
        name        = "AWSManagedRulesCommonRuleSet"
        vendor_name = "AWS"
      }
    }
    visibility_config {
      cloudwatch_metrics_enabled = true
      metric_name                = "${var.name}-AWSManagedRulesCommonRuleSet"
      sampled_requests_enabled   = true
    }
  }

  # Rule: Amazon IP Reputation List
  rule {
    name     = "AWS-AWSManagedRulesAmazonIpReputationList"
    priority = 20
    override_action {
      none {}
    }
    statement {
      managed_rule_group_statement {
        name        = "AWSManagedRulesAmazonIpReputationList"
        vendor_name = "AWS"
      }
    }
    visibility_config {
      cloudwatch_metrics_enabled = true
      metric_name                = "${var.name}-AWSManagedRulesAmazonIpReputationList"
      sampled_requests_enabled   = true
    }
  }

  # Rule: Known Bad Inputs
  rule {
    name     = "AWS-AWSManagedRulesKnownBadInputsRuleSet"
    priority = 30
    override_action {
      none {}
    }
    statement {
      managed_rule_group_statement {
        name        = "AWSManagedRulesKnownBadInputsRuleSet"
        vendor_name = "AWS"
      }
    }
    visibility_config {
      cloudwatch_metrics_enabled = true
      metric_name                = "${var.name}-AWSManagedRulesKnownBadInputsRuleSet"
      sampled_requests_enabled   = true
    }
  }

  visibility_config {
    cloudwatch_metrics_enabled = true
    metric_name                = var.name
    sampled_requests_enabled   = true
  }

  tags = var.tags
}

data "aws_caller_identity" "current" {}

data "aws_iam_policy_document" "waf_logs_kms" {
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
      identifiers = ["logs.amazonaws.com"]
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

resource "aws_kms_key" "waf_logs" {
  description         = "KMS key for WAF CloudWatch log group encryption"
  enable_key_rotation = true
  policy              = data.aws_iam_policy_document.waf_logs_kms.json
}

resource "aws_cloudwatch_log_group" "waf" {
  name              = "aws-waf-logs-${var.name}"
  retention_in_days = 7
  kms_key_id        = aws_kms_key.waf_logs.arn

  tags = var.tags
}

resource "aws_wafv2_web_acl_logging_configuration" "main" {
  log_destination_configs = [aws_cloudwatch_log_group.waf.arn]
  resource_arn            = aws_wafv2_web_acl.main.arn

  logging_filter {
    default_behavior = "DROP"

    filter {
      behavior = "KEEP"

      condition {
        action_condition {
          action = "BLOCK"
        }
      }

      condition {
        action_condition {
          action = "COUNT"
        }
      }

      requirement = "MEETS_ANY"
    }
  }
}
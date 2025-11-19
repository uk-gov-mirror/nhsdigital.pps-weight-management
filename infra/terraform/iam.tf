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

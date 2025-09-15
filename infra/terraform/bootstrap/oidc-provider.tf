####################################################################
#
# OIDC Provider for GitHub Actions
# --------------------------------
# 
# Create backend resources (run once)
#
# > cd infra/terraform/bootstrap
# > terraform init
# > terraform apply -auto-approve
# 
####################################################################

# Configure the IAM OpenID Connect (OIDC) provider for GitHub Actions.
# This is the identity provider that GitHub will use to authenticate with AWS.
resource "aws_iam_openid_connect_provider" "github" {
  url             = "https://token.actions.githubusercontent.com"
  client_id_list  = ["sts.amazonaws.com"]

  thumbprint_list = [
    "1c58a3a8518e8759bf075b76b7507d40211f0514",
    "6938fd4d98bab03faadb97b34396831e3780aea1"
  ]
}

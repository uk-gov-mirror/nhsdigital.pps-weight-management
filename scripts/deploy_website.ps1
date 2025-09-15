# Deploy website
# .\scripts\deploy_website.ps1 -EnvName dev-jb

param(
  [Parameter(Mandatory = $true)]
  [string]$EnvName                           # e.g. dev-jb, poc, pr-nn
)

$env:ENV = $EnvName
Write-Host "Using environment: $EnvName"

$TF_DIR = ".\infra\terraform"
$TF_DIST_ID_NAME = "cloudfront_distribution_id"
$TF_CF_URL_NAME = "cloudfront_url"

$env:AWS_PROFILE = 'admin-pps-wm'
$env:AWS_REGION  = 'eu-west-2'
$env:AWS_SDK_LOAD_CONFIG = '1'

aws sso login --profile $env:AWS_PROFILE

Push-Location $TF_DIR
try {
    $env:DISTRIBUTION_ID = (terraform output -raw $TF_DIST_ID_NAME).Trim()
    $env:SITE_URL = (terraform output -raw $TF_CF_URL_NAME).Trim()
} catch {
    Write-Error "Failed to read Terraform output '$TF_DIST_ID_NAME' in '$TF_DIR'. Ensure 'terraform output' works and the output exists."
    exit 1
} finally {
    Pop-Location
}

if ([string]::IsNullOrWhiteSpace($env:DISTRIBUTION_ID)) {
    Write-Error "Terraform output '$TF_DIST_ID_NAME' returned nothing."
    exit 1
}

Write-Host "Using CloudFront Distribution ID: $($env:DISTRIBUTION_ID)"

aws s3 sync "web/" "s3://nhse-pps-wm-${env:ENV}-site/" --delete
aws cloudfront create-invalidation --distribution-id ${env:DISTRIBUTION_ID} --paths "/*"

Write-Host "Site published to $($env:SITE_URL)"

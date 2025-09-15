# Deploy Lambda 
# (Also builds and deploys any infrastructure changes)
# .\scripts\deploy_lambda.ps1 -EnvName dev-jb

param(
  [Parameter(Mandatory = $true)]
  [string]$EnvName                           # e.g. dev-jb, poc, pr-nn
)

$env:ENV = $EnvName
Write-Host "Using environment: $EnvName"

# Exit immediately if a command returns a non-zero exit status.
$ErrorActionPreference = "Stop"

$TF_DIR = ".\infra\terraform"
$TF_CF_URL_NAME = "cloudfront_url"

# build the lambda
Write-Host "Building lambda zip files ..."
.\scripts\build_lambda_zip.ps1

# Deploy the infrastructure

$env:AWS_PROFILE = 'admin-pps-wm'
$env:AWS_REGION  = 'eu-west-2'
$env:AWS_SDK_LOAD_CONFIG = '1'

aws sso login --profile $env:AWS_PROFILE

Push-Location $TF_DIR
try {
    Write-Host "Deploying infrastructure ..."

    terraform init -reconfigure -backend-config="bucket=nhse-pps-wm-terraform-state-bucket" -backend-config="key=$env:ENV/terraform.tfstate" -backend-config="region=eu-west-2"
    terraform apply -auto-approve -var-file="envs/$env:ENV/terraform.tfvars"
	
	$env:SITE_URL = (terraform output -raw $TF_CF_URL_NAME).Trim()

} catch {
    Write-Error "Failed to deploy infrastructure"
    exit 1
} finally {
    Pop-Location
}

Write-Host "Ensuring Cognito test user exists..."

# Resolve paths (run the Python script relative to this .ps1 file)
$RepoRoot = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path
$CreateUserPy = Join-Path $RepoRoot 'scripts/create_cognito_test_user.py'

$env:TF_VAR_project = 'nhse-pps-wm'
$env:TF_VAR_env     = $EnvName

python3 $CreateUserPy
if ($LASTEXITCODE -ne 0) { throw "create_cognito_test_user.py failed ($LASTEXITCODE)" }

Write-Host "Site updated $($env:SITE_URL)"


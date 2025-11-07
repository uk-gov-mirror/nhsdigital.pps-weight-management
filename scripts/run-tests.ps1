# Run tests
# .\scripts\run-tests.ps1 -EnvName dev-jb -Api -Ui -InstallBrowsers
# .\scripts\run-tests.ps1 -EnvName pr-38 -DjangoBaseUrl http://127.0.0.1:8000 -Api -Ui -InstallBrowsers

param(
  [Parameter(Mandatory = $true)]
  [string]$EnvName,                           # e.g. dev-jb, poc, pr-nn

  [string]$AwsRegion     = "eu-west-2",
  [string]$TfStateBucket = "nhse-pps-wm-terraform-state-bucket",
  [string]$TfLockTable   = "nhse-pps-wm-terraform-lock",
  [string]$DjangoBaseUrl,
  [string]$CognitoClientId,
  [string]$CognitoUsername = "test-user",
  [string]$CognitoPassword = "MySecurePassword123!",

  [switch]$Api,
  [switch]$Ui,
  [switch]$InstallBrowsers
)

$ErrorActionPreference = "Stop"

function Write-Info($msg) { Write-Host "-> $msg" -ForegroundColor Cyan }
function Write-Warn($msg) { Write-Host "!! $msg" -ForegroundColor Yellow }

# 1) Resolve env vars (Terraform outputs or manual overrides)
if ($TfStateBucket -and $TfLockTable) {
  Write-Info "Resolving outputs from Terraform for env '$EnvName'..."
  Push-Location -Path "infra/terraform"
  try {
    terraform init `
      -reconfigure `
      -backend-config="bucket=$TfStateBucket" `
      -backend-config="dynamodb_table=$TfLockTable" `
      -backend-config="key=$EnvName/terraform.tfstate" `
      -backend-config="region=$AwsRegion" | Out-Null

    if (-not $DjangoBaseUrl) {
      $DjangoBaseUrl = terraform output -raw cloudfront_url
    }
    if (-not $CognitoClientId) {
      try { $CognitoClientId = terraform output -raw cognito_client_id_ci } catch { $CognitoClientId = $null }
    }
  }
  finally { Pop-Location }
}
elseif (-not $DjangoBaseUrl) {
  throw "Set -DjangoBaseUrl or provide Terraform backend details to auto-resolve it."
}

# 2) Export environment variables for this PowerShell session
Write-Info "Configuring environment variables..."
$env:AWS_REGION        = $AwsRegion
$env:DJANGO_BASE_URL   = $DjangoBaseUrl.TrimEnd('/')
$env:API_PREFIX_PUBLIC = "/public/api"
$env:API_PREFIX_SECURE = "/secure/api"

if ($CognitoClientId) { $env:COGNITO_CLIENT_ID = $CognitoClientId }
$env:COGNITO_USERNAME  = $CognitoUsername
$env:COGNITO_PASSWORD  = $CognitoPassword

Write-Host "DJANGO_BASE_URL      = $env:DJANGO_BASE_URL"
Write-Host "API_PREFIX_PUBLIC    = $env:API_PREFIX_PUBLIC"
Write-Host "API_PREFIX_SECURE    = $env:API_PREFIX_SECURE"
if ($env:COGNITO_CLIENT_ID) { Write-Host "COGNITO_CLIENT_ID     = $env:COGNITO_CLIENT_ID" }
Write-Host "COGNITO_USERNAME     = $env:COGNITO_USERNAME"

# 3) Install deps (once per machine)
Write-Info "Installing npm dependencies..."
npm ci

# 4) Playwright browsers (skip if already installed)
if ($InstallBrowsers -or $Ui) {
  Write-Info "Ensuring Playwright browsers are installed..."
  npx playwright install
}

# 5) Warm up endpoints (optional)
Write-Info "Warming up endpoints (non-blocking)..."
try {
  curl.exe -fsS -m 8 "$($env:DJANGO_BASE_URL)" | Out-Null
  curl.exe -fsS -m 8 "$($env:DJANGO_BASE_URL)$($env:API_PREFIX_PUBLIC)/ping" | Out-Null
} catch { }

# 6) Run tests
$runApi = $true
$runUi  = $true
if ($Api -and -not $Ui) { $runUi = $false }
if ($Ui  -and -not $Api) { $runApi = $false }

if ($runApi) {
  Write-Info "Running Jest API tests..."
  npm run test:ci:api
}

if ($runUi) {
  Write-Info "Running Playwright UI tests..."
  npm run test:ci:ui
}

Write-Host "Done." -ForegroundColor Green

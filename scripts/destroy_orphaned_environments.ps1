# Delete orphaned ephemeral environments

$TF_STATE_BUCKET     = "nhse-pps-wm-terraform-state-bucket"
$TF_STATE_LOCK_TABLE = "nhse-pps-wm-terraform-state-lock-table"
$AWS_REGION          = "eu-west-2"
$PROJECT             = "nhse-pps-wm"
$TF_DIR              = "infra/terraform"
$GhOwner             = "NHSDigital"
$GhRepo              = "pps-htsh"

$orphans = @('pr-20','pr-21','pr-22')

function Remove-PrEnv {
  param([Parameter(Mandatory=$true)][string]$EnvName)

  Write-Host "=== Destroying $EnvName ===" -ForegroundColor Cyan
  Push-Location $TF_DIR

  terraform init -reconfigure -backend-config="bucket=$TF_STATE_BUCKET" -backend-config="dynamodb_table=$TF_STATE_LOCK_TABLE" -backend-config="key=$EnvName/terraform.tfstate" -backend-config="region=$AWS_REGION"

  $env:TF_VAR_project  = $PROJECT
  $env:TF_VAR_region   = $AWS_REGION
  $env:TF_VAR_env      = $EnvName
  $env:TF_VAR_gh_owner = $GhOwner
  $env:TF_VAR_gh_repo  = $GhRepo
  terraform destroy -auto-approve

  & "$PSScriptRoot\delete_pr_state.ps1" -EnvName $envName -DoSsoLogin:$false -ErrorAction Stop

  Pop-Location
  Write-Host "=== Destroyed $EnvName ===" -ForegroundColor Green
}

# Preview what you’re about to destroy
"Will destroy these envs:`n$($orphans -join "`n")"

# Confirm
$ans = Read-Host "Proceed? (y/N)"
if ($ans -match '^(y|yes)$') {
  foreach ($envName in $orphans) { Remove-PrEnv -EnvName $envName }
} else {
  "Aborted."
}

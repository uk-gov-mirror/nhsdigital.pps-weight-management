# Reset Terraform state if terraform reports a checksum mismatch
# .\reset_terraform_state.ps1 -PR_ENV poc -Checksum afbf30a547125e7ab7b042d3ca4649d9

[CmdletBinding()]
param(
  [Parameter(Mandatory = $true)][string]$PR_ENV,
  [Parameter(Mandatory = $true)][string]$Checksum
)

$env:AWS_PROFILE = 'admin-pps-wm'
$env:AWS_REGION  = 'eu-west-2'
$env:AWS_SDK_LOAD_CONFIG = '1'

aws sso login --profile $env:AWS_PROFILE

# Constants
$Table  = "nhse-pps-wm-terraform-state-lock-table"
$Bucket = "nhse-pps-wm-terraform-state-bucket"
$Region = "eu-west-2"

# Build the LockID as used in your table (bucket + key + "-md5")
$Key        = "$PR_ENV/terraform.tfstate"
$LockId     = "$Bucket/$Key-md5"

Write-Host "Table:   $Table"
Write-Host "Region:  $Region"
Write-Host "LockID:  $LockId"
Write-Host "Digest:  $Checksum"
Write-Host ""

# Try to read the existing item
$respJson = aws dynamodb get-item `
  --table-name $Table `
  --key "{`"LockID`":{`"S`":`"$LockId`"}} " `
  --region $Region `
  --output json 2>$null

$exists = $false
if ($LASTEXITCODE -eq 0 -and $respJson) {
  $resp = $respJson | ConvertFrom-Json
  if ($resp.Item) {
    $exists = $true
    $current = $resp.Item.Digest.S
    Write-Host "Current Digest: $current"
  }
}

# Update if exists
if ($exists) {
  Write-Host "Updating Digest..." -ForegroundColor Yellow
  $updateOut = aws dynamodb update-item `
    --table-name $Table `
    --key "{`"LockID`":{`"S`":`"$LockId`"}} " `
    --update-expression "SET #D = :d" `
    --expression-attribute-names "{`"#D`":`"Digest`"}" `
    --expression-attribute-values "{`":d`":{`"S`":`"$Checksum`"}}" `
    --region $Region --output json
  if ($LASTEXITCODE -ne 0) {
    throw "Failed to update Digest. Output:`n$updateOut"
  }
  Write-Host " Updated Digest to '$Checksum'."
} else {
  Write-Host "Item not found." -ForegroundColor Yellow
}

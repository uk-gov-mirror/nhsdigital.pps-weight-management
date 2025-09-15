# List orphaned ephemeral environments

$env:AWS_PROFILE = 'admin-pps-wm'
$env:AWS_REGION  = 'eu-west-2'
$env:AWS_SDK_LOAD_CONFIG = '1'

aws sso login --profile $env:AWS_PROFILE

$Bucket = "nhse-pps-wm-terraform-state-bucket"

# 1) PR preview envs from your S3 state (first path segment before /terraform.tfstate)
$prEnvs = aws s3api list-objects-v2 --bucket $Bucket `
    --query 'Contents[?ends_with(Key,`/terraform.tfstate`)].Key' --output text `
    | ForEach-Object { $_ -split "`t" } `
    | ForEach-Object { ($_ -split '/')[0] } `
    | Where-Object { $_ -like 'pr-*' } `
    | Sort-Object -Unique

# 2) Open PR env names (e.g., "pr-123")
$open = gh pr list -s open --json number `
| ConvertFrom-Json `
| ForEach-Object { "pr-$($_.number)" } `
| Sort-Object -Unique

# Ensure we have arrays (not $null)
$prEnvs = @($prEnvs | Where-Object { $_ })
$open   = @($open   | Where-Object { $_ })

# 3) Orphans = in S3 state but NOT currently open in GitHub
$orphans = @(
  Compare-Object -ReferenceObject $prEnvs -DifferenceObject $open -PassThru | Where-Object { $_ } | Select-Object -Skip 1
)

if (-not $orphans -or $orphans.Count -eq 0) {
  Write-Host "No orphaned preview environments."
  return
}

"Orphan envs:`n$($orphans -join "`n")"
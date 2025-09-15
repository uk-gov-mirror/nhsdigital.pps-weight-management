# List Terraform states in bucket

$env:AWS_PROFILE = 'admin-pps-wm'
$env:AWS_REGION  = 'eu-west-2'
$env:AWS_SDK_LOAD_CONFIG = '1'

aws sso login --profile $env:AWS_PROFILE

$Bucket = "nhse-pps-wm-terraform-state-bucket"

$states = aws s3api list-objects-v2 --bucket $Bucket `
  --query 'Contents[?ends_with(Key,`/terraform.tfstate`)]' | ConvertFrom-Json

$states | ForEach-Object {
  [pscustomobject]@{
    Env          = $_.Key.Split('/')[0]
    Key          = $_.Key
    Size         = $_.Size
    LastModified = $_.LastModified
  }
} | Sort-Object Env | Format-Table -Auto

# Unique env names
$states | ForEach-Object { $_.Key.Split('/')[0] } | Sort-Object -Unique
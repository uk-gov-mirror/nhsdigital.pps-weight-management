# Delete Terraform state from bucket and lock table

param(
  [Parameter(Mandatory = $true)]
  [string]$EnvName,                         # e.g. dev-jb, poc, pr-nn
  
  [bool]$DoSsoLogin = $true                 # default: run aws sso login
)

$env:PR_ENV = $EnvName
$env:TF_STATE_BUCKET = "nhse-pps-wm-terraform-state-bucket"
Write-Host "Using environment: $EnvName"

$ErrorActionPreference = 'Stop'

# Only run for pr-* environments
if ($env:PR_ENV -notlike 'pr-*') {
    Write-Host "EnvName '$($env:PR_ENV)' does not start with 'pr-'. Skipping remote state cleanup."
    return
}

$env:AWS_PROFILE = 'admin-pps-wm'
$env:AWS_REGION  = 'eu-west-2'
$env:AWS_SDK_LOAD_CONFIG = '1'

if ($DoSsoLogin) {
  aws sso login --profile $env:AWS_PROFILE
}

# Inputs (mirror the GitHub Action env block)
$BUCKET = $env:TF_STATE_BUCKET
$KEY    = "$($env:PR_ENV)/terraform.tfstate"

Write-Host "Cleaning remote state s3://$BUCKET/$KEY"

# Helper: get ALL versions + delete markers for a single key, across pagination
function Get-AllObjectVersions {
    param(
        [Parameter(Mandatory = $true)][string]$Bucket,
        [Parameter(Mandatory = $true)][string]$Key
    )

    $versions      = @()
    $deleteMarkers = @()
    $keyMarker = $null
    $versionIdMarker = $null

    do {
        $args = @('s3api','list-object-versions','--bucket', $Bucket, '--prefix', $Key, '--output','json')
        if ($keyMarker) {
            $args += @('--key-marker', $keyMarker, '--version-id-marker', $versionIdMarker)
        }

        $resp = aws @args | ConvertFrom-Json

        if ($resp.Versions) {
            $versions += $resp.Versions | Where-Object { $_.Key -eq $Key -and $_.VersionId }
        }
        if ($resp.DeleteMarkers) {
            $deleteMarkers += $resp.DeleteMarkers | Where-Object { $_.Key -eq $Key -and $_.VersionId }
        }

        $isTruncated = [bool]$resp.IsTruncated
        if ($isTruncated) {
            $keyMarker       = $resp.NextKeyMarker
            $versionIdMarker = $resp.NextVersionIdMarker
        }
    } while ($isTruncated)

    # return a single array of objects with Key and VersionId
    return @($versions + $deleteMarkers) | ForEach-Object {
        [pscustomobject]@{ Key = $_.Key; VersionId = $_.VersionId }
    }
}

# Loop until there are no more versions or delete markers
while ($true) {
    $allObjects = Get-AllObjectVersions -Bucket $BUCKET -Key $KEY

    if (-not $allObjects -or $allObjects.Count -eq 0) {
        Write-Host "No more versions or delete markers found. Deletion complete."
        break
    }

    Write-Host ("Found {0} items to delete..." -f $allObjects.Count)

    # S3 delete-objects allows max 1000 per request — batch accordingly
    for ($i = 0; $i -lt $allObjects.Count; $i += 1000) {
        $end   = [Math]::Min($i + 999, $allObjects.Count - 1)
        $batch = $allObjects[$i..$end]

        # Build payload JSON
        $payload = [ordered]@{
            Objects = $batch | ForEach-Object { @{ Key = $_.Key; VersionId = $_.VersionId } }
            Quiet   = $true
        } | ConvertTo-Json -Depth 5

        $tmpFile = [System.IO.Path]::GetTempFileName()

        # Write UTF-8 *without* BOM (works in Windows PowerShell and PowerShell 7+)
        $utf8NoBom = New-Object System.Text.UTF8Encoding($false)
        [System.IO.File]::WriteAllText($tmpFile, $payload, $utf8NoBom)

        try {
            # Use a Windows-friendly file URI (slashes not backslashes)
            $paramFileUri = "file://$((Resolve-Path -LiteralPath $tmpFile).Path -replace '\\','/')"
            aws s3api delete-objects --bucket $BUCKET --delete $paramFileUri | Out-Host
        }
        finally {
            Remove-Item -LiteralPath $tmpFile -ErrorAction SilentlyContinue
        }
    }
}

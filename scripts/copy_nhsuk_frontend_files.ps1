param(
    # Base directory = current working directory where script is RUN
    [string]$Base = (Get-Location).Path,

    # Relative paths from base directory
    [string]$SrcRel  = "node_modules\nhsuk-frontend\dist\nhsuk",
    [string]$DestRel = "django_app\static",
    [string]$ScssRel = "django_app\static\assets\sass\nhsuk-frontend"
)

$SrcRoot  = Join-Path $Base $SrcRel
$DestRoot = Join-Path $Base $DestRel
$ScssRoot = Join-Path $Base $ScssRel

Write-Host "Working directory: $Base"
Write-Host "Source          : $SrcRoot"
Write-Host "Destination     : $DestRoot"
Write-Host "SCSS            : $ScssRoot"
Write-Host ""

if (-not (Test-Path $SrcRoot)) {
    Write-Error "Source path '$SrcRoot' does not exist. Run script from your project root."
    exit 1
}

# Allowed/deployable file types
$allowedExtensions = @(
    '.css', '.js', '.json',
    '.png', '.svg', '.ico',
    '.jpg', '.jpeg', '.gif',
    '.woff', '.woff2', '.ttf', 
	'.eot', '.map'
)

# Ensure destination root exists
if (-not (Test-Path $DestRoot)) {
    New-Item -ItemType Directory -Path $DestRoot -Force | Out-Null
}

Write-Host "Copying nhsuk-frontend dist assets..." -ForegroundColor Cyan

Get-ChildItem -Path $SrcRoot -Recurse -File | Where-Object {
    $allowedExtensions -contains $_.Extension.ToLower()
} | ForEach-Object {
    $relativePath = $_.FullName.Substring($SrcRoot.Length).TrimStart('\','/')
    $destPath     = Join-Path $DestRoot $relativePath
    $destDir      = Split-Path $destPath -Parent

    if (-not (Test-Path $destDir)) {
        New-Item -ItemType Directory -Path $destDir -Force | Out-Null
    }

    Write-Host "  -> $relativePath"
    Copy-Item -Path $_.FullName -Destination $destPath -Force
}

Write-Host ""
Write-Host "Done. Files copied to '$DestRoot' with structure preserved." -ForegroundColor Green

# Allowed/deployable file types
$allowedExtensions = @(
    '.scss', '.sass'
)

# Ensure destination root exists
if (-not (Test-Path $ScssRoot)) {
    New-Item -ItemType Directory -Path $ScssRoot -Force | Out-Null
}

Write-Host "Copying nhsuk-frontend SCSS dist assets..." -ForegroundColor Cyan

Get-ChildItem -Path $SrcRoot -Recurse -File | Where-Object {
    $allowedExtensions -contains $_.Extension.ToLower()
} | ForEach-Object {
    $relativePath = $_.FullName.Substring($SrcRoot.Length).TrimStart('\','/')
    $destPath     = Join-Path $ScssRoot $relativePath
    $destDir      = Split-Path $destPath -Parent

    if (-not (Test-Path $destDir)) {
        New-Item -ItemType Directory -Path $destDir -Force | Out-Null
    }

    Write-Host "  -> $relativePath"
    Copy-Item -Path $_.FullName -Destination $destPath -Force
}

Write-Host ""
Write-Host "Done. SCSS files copied to '$ScssRoot' with structure preserved." -ForegroundColor Green

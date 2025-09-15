# Exit immediately if a command returns a non-zero exit status.
$ErrorActionPreference = "Stop"

## Build api.zip

# Navigate to the 'api' directory.
Set-Location -Path ".\lambda\api"

# Check for package-lock.json and install dependencies.
if (Test-Path -Path ".\package-lock.json") {
    npm ci
} else {
    npm install
}

# Run the build script.
npm run build

# Navigate back to the parent directory.
Set-Location -Path "..\.."

# Remove the existing api.zip file.
Remove-Item -Path ".\api.zip" -Force -ErrorAction SilentlyContinue

# Navigate to 'api/dist', zip the contents, then navigate back.
Compress-Archive -Path ".\lambda\api\dist\*" -DestinationPath ".\api.zip" -Force

## Build daily.zip

# Navigate to the 'daily' directory.
Set-Location -Path ".\lambda\daily"

# Check for package-lock.json and install dependencies.
if (Test-Path -Path ".\package-lock.json") {
    npm ci
} else {
    npm install
}

# Run the build script.
npm run build

# Navigate back to the parent directory.
Set-Location -Path "..\.."

# Remove the existing daily.zip file.
Remove-Item -Path ".\daily.zip" -Force -ErrorAction SilentlyContinue

# Navigate to 'daily/dist', zip the contents, then navigate back.
Compress-Archive -Path ".\lambda\daily\dist\*" -DestinationPath ".\daily.zip" -Force

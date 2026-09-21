param(
    [string]$LocalEndpoint = "http://127.0.0.1:9000",
    [string]$RemoteEndpoint = "http://REMOTE_HOST_IP:9000",
    [string]$AccessKey,
    [string]$SecretKey,
    [string]$EnvFilePath,
    [string]$Bucket = "jobs-bronze"
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

# Default .env path: backend/.env relative to this script file.
if (-not $EnvFilePath) {
    $scriptDir = Split-Path -Parent $PSCommandPath
    $backendDir = (Resolve-Path (Join-Path $scriptDir "..\..")).Path
    $EnvFilePath = Join-Path $backendDir ".env"
}

# Try to load credentials from .env when params/env vars are not set.
if ((-not $AccessKey -or -not $SecretKey) -and (Test-Path $EnvFilePath)) {
    $envMap = @{}
    foreach ($line in Get-Content $EnvFilePath) {
        $trim = $line.Trim()
        if (-not $trim -or $trim.StartsWith("#")) { continue }
        $idx = $trim.IndexOf("=")
        if ($idx -lt 1) { continue }
        $k = $trim.Substring(0, $idx).Trim()
        $v = $trim.Substring($idx + 1)
        $envMap[$k] = $v
    }
    if (-not $AccessKey -and $envMap.ContainsKey("MINIO_ROOT_USER")) {
        $AccessKey = $envMap["MINIO_ROOT_USER"]
    }
    if (-not $SecretKey -and $envMap.ContainsKey("MINIO_ROOT_PASSWORD")) {
        $SecretKey = $envMap["MINIO_ROOT_PASSWORD"]
    }
}

if (-not $AccessKey) { $AccessKey = $env:MINIO_ROOT_USER }
if (-not $SecretKey) { $SecretKey = $env:MINIO_ROOT_PASSWORD }

if (-not $AccessKey -or -not $SecretKey) {
    Write-Error "Missing credentials. Pass -AccessKey/-SecretKey or set MINIO_ROOT_USER/MINIO_ROOT_PASSWORD."
}

Write-Host "Checking endpoints..." -ForegroundColor Cyan
try {
    $null = Invoke-WebRequest -Uri "$LocalEndpoint/minio/health/live" -UseBasicParsing -TimeoutSec 5
} catch {
    Write-Error "Local MinIO is not reachable at $LocalEndpoint"
}

try {
    $null = Invoke-WebRequest -Uri "$RemoteEndpoint/minio/health/live" -UseBasicParsing -TimeoutSec 5
} catch {
    Write-Error "Remote MinIO is not reachable at $RemoteEndpoint (open 9000 in server security group)."
}

# Docker container cannot use localhost of Windows host directly.
$LocalEndpointForContainer = $LocalEndpoint `
    -replace '://127\.0\.0\.1(?=[:/]|$)', '://host.docker.internal' `
    -replace '://localhost(?=[:/]|$)', '://host.docker.internal'

Write-Warning "Sync miroir strict: les objets supprimes en local seront aussi supprimes sur le serveur."

$script = @"
set -e
mc alias set local "$LocalEndpointForContainer" "$AccessKey" "$SecretKey"
mc alias set remote "$RemoteEndpoint" "$AccessKey" "$SecretKey"
mc mb --ignore-existing "local/$Bucket"
mc mb --ignore-existing "remote/$Bucket"
mc mirror --overwrite --remove --watch=false "local/$Bucket" "remote/$Bucket"
mc ls --recursive --summarize "remote/$Bucket"
"@

Write-Host "Starting mirror local/$Bucket -> remote/$Bucket ..." -ForegroundColor Yellow
docker run --rm `
  --entrypoint /bin/sh `
  minio/mc:latest `
  -c $script

if ($LASTEXITCODE -ne 0) {
    Write-Error "Sync failed (mc exit code: $LASTEXITCODE)."
}

Write-Host "Sync completed." -ForegroundColor Green

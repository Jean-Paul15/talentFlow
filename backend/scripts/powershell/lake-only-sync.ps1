param(
    [string]$RemoteHost = "REMOTE_HOST_IP",
    [string]$Bucket = "jobs-bronze"
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$localMinio = "http://127.0.0.1:9000"
$remoteMinio = "http://$($RemoteHost):9000"
$remoteLake = "http://$($RemoteHost):8004"
$remoteStreamlit = "http://$($RemoteHost):8501"

$scriptDir = Split-Path -Parent $PSCommandPath
$syncScript = Join-Path $scriptDir "sync-minio-bronze.ps1"

Write-Host "1/3 Sync bucket '$Bucket' -> $remoteMinio" -ForegroundColor Cyan
& $syncScript `
    -LocalEndpoint $localMinio `
    -RemoteEndpoint $remoteMinio `
    -Bucket $Bucket

Write-Host "2/3 Check Lake API health" -ForegroundColor Cyan
$health = Invoke-RestMethod -Uri "$remoteLake/health" -TimeoutSec 10
$stats = Invoke-RestMethod -Uri "$remoteLake/api/bronze/stats" -TimeoutSec 20
Write-Host ("Lake API: {0} | bucket={1} | total_objects={2}" -f $health.status, $stats.bucket, $stats.total_objects) -ForegroundColor Green

Write-Host "3/3 URLs" -ForegroundColor Cyan
Write-Host "Streamlit: $remoteStreamlit"
Write-Host "Lake API docs: $remoteLake/docs"

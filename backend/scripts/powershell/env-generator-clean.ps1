# Module: Generateur .env minimal (PowerShell)

function Generate-RandomSecret {
    $bytes = New-Object byte[] 32
    [Security.Cryptography.RandomNumberGenerator]::Create().GetBytes($bytes)
    return [Convert]::ToBase64String($bytes)
}

function Prompt-WithDefault {
    param([string]$Prompt, [string]$Default)
    $value = Read-Host "$Prompt [$Default]"
    if ([string]::IsNullOrWhiteSpace($value)) { return $Default }
    return $value
}

function New-EnvFile {
    param([string]$EnvPath)

    $JWT_SECRET = Generate-RandomSecret
    $POSTGRES_PASSWORD = Generate-RandomSecret
    $MINIO_ROOT_USER = "talentflow_" + -join ((1..4) | ForEach-Object { '{0:x}' -f (Get-Random -Maximum 16) })
    $MINIO_ROOT_PASSWORD = Generate-RandomSecret
    $GRAFANA_PASSWORD = Generate-RandomSecret

    Write-Host "Recommendation (Gemini)" -ForegroundColor Yellow
    $GEMINI_API_KEY = Prompt-WithDefault "Gemini API Key principale" ""
    $GEMINI_API_KEY_FALLBACK = Prompt-WithDefault "Gemini API Key secondaire" ""
    Write-Host "Data-cleaning (Mistral)" -ForegroundColor Yellow
    $MISTRAL_API_KEY = Prompt-WithDefault "Mistral API Key" ""

    $content = @"
# TalentFlow Environment Configuration
# Genere automatiquement le $(Get-Date)
JWT_SECRET=$JWT_SECRET
POSTGRES_PASSWORD=$POSTGRES_PASSWORD
MINIO_ROOT_USER=$MINIO_ROOT_USER
MINIO_ROOT_PASSWORD=$MINIO_ROOT_PASSWORD
GRAFANA_PASSWORD=$GRAFANA_PASSWORD
LLM_PROVIDER=gemini
LLM_PROVIDER_ORDER=gemini
LLM_FALLBACK_PROVIDER=gemini
GEMINI_API_KEY=$GEMINI_API_KEY
GEMINI_API_KEY_FALLBACK=$GEMINI_API_KEY_FALLBACK
GEMINI_API_KEYS=
GEMINI_MODEL=gemini-2.5-flash
GEMINI_MODEL_PRIORITY=gemini-2.5-flash,gemini-2.5-flash-lite,gemini-2.0-flash
GEMINI_BASE_URL=https://generativelanguage.googleapis.com
GEMINI_TIMEOUT_SECONDS=45
GEMINI_MAX_RETRIES=2
GEMINI_RETRY_BASE_SECONDS=1.0
DATA_CLEANING_LLM_PROVIDER=mistral
DATA_CLEANING_LLM_ENABLED=false
MISTRAL_API_KEY=$MISTRAL_API_KEY
MISTRAL_MODEL=mistral-small-latest
MISTRAL_TIMEOUT_SECONDS=45
MISTRAL_MAX_RETRIES=2
MISTRAL_RETRY_BASE_SECONDS=1.0
LLM_MAX_TOKENS=500
LLM_TEMPERATURE=0.2
ALLOWED_ORIGINS=*
POSTGRES_USER=talentflow
POSTGRES_DB=talentflow
POSTGRES_HOST=postgres
POSTGRES_PORT=5432
REDIS_HOST=redis
REDIS_PORT=6379
REDIS_URL=redis://redis:6379
MINIO_ENDPOINT=minio:9000
MINIO_SECURE=false
MINIO_HOST=minio:9000
MINIO_ACCESS_KEY=$MINIO_ROOT_USER
MINIO_SECRET_KEY=$MINIO_ROOT_PASSWORD
MINIO_BUCKET_BRONZE=jobs-bronze
MINIO_BUCKET_SILVER=jobs-silver
MONGO_HOST=mongodb
MONGO_PORT=27017
MONGO_DB=talentflow_silver
MONGODB_URI=mongodb://mongodb:27017/talentflow_silver
QDRANT_URL=http://qdrant:6333
"@

    Set-Content -Path $EnvPath -Value $content
    Write-Host "Fichier .env cree: $EnvPath" -ForegroundColor Green
}

$scriptPath = Split-Path -Parent $MyInvocation.MyCommand.Path
$projectRoot = Split-Path -Parent (Split-Path -Parent (Split-Path -Parent $scriptPath))
$envPath = Join-Path $projectRoot ".env"

if (Test-Path $envPath) {
    Write-Host "Le fichier .env existe deja." -ForegroundColor Yellow
    $overwrite = Read-Host "Voulez-vous le remplacer? (oui/non)"
    if ($overwrite -notin @("oui", "o")) { exit 0 }
}

New-EnvFile -EnvPath $envPath

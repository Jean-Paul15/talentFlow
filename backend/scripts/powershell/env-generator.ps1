# Module: Generateur .env automatique (PowerShell)

function Generate-RandomSecret {
    $bytes = New-Object byte[] 32
    [Security.Cryptography.RandomNumberGenerator]::Create().GetBytes($bytes)
    return [Convert]::ToBase64String($bytes)
}

function Prompt-WithDefault {
    param(
        [string]$Prompt,
        [string]$Default
    )

    $value = Read-Host "$Prompt [$Default]"
    if ([string]::IsNullOrWhiteSpace($value)) {
        return $Default
    }
    return $value
}

function New-EnvFile {
    param([string]$EnvPath)

    Write-Host "Generation du fichier .env..." -ForegroundColor Cyan

    $JWT_SECRET = Generate-RandomSecret
    $POSTGRES_PASSWORD = Generate-RandomSecret
    $MINIO_ROOT_USER = "talentflow_" + -join ((1..4) | ForEach-Object { '{0:x}' -f (Get-Random -Maximum 16) })
    $MINIO_ROOT_PASSWORD = Generate-RandomSecret
    $GRAFANA_PASSWORD = Generate-RandomSecret

    Write-Host ""
    Write-Host "Recommendation (Gemini)" -ForegroundColor Yellow
    $GEMINI_API_KEY = Prompt-WithDefault "Gemini API Key principale" ""
    $GEMINI_API_KEY_FALLBACK = Prompt-WithDefault "Gemini API Key secondaire" ""
    $GEMINI_MODEL = Prompt-WithDefault "Gemini model" "gemini-2.5-flash"

    Write-Host ""
    Write-Host "Data-cleaning (Mistral)" -ForegroundColor Yellow
    $MISTRAL_API_KEY = Prompt-WithDefault "Mistral API Key" ""
    $MISTRAL_MODEL = Prompt-WithDefault "Mistral model" "mistral-small-latest"
    $DATA_CLEANING_LLM_ENABLED = Prompt-WithDefault "Activer le LLM de nettoyage ? (true/false)" "false"

    $content = @"
# TalentFlow Environment Configuration
# Genere automatiquement le $(Get-Date)

# ==== SECRETS ====
JWT_SECRET=$JWT_SECRET
POSTGRES_PASSWORD=$POSTGRES_PASSWORD
MINIO_ROOT_USER=$MINIO_ROOT_USER
MINIO_ROOT_PASSWORD=$MINIO_ROOT_PASSWORD
GRAFANA_PASSWORD=$GRAFANA_PASSWORD

# ==== RECOMMENDATION / GEMINI ====
LLM_PROVIDER=gemini
LLM_PROVIDER_ORDER=gemini
LLM_FALLBACK_PROVIDER=gemini
GEMINI_API_KEY=$GEMINI_API_KEY
GEMINI_API_KEY_FALLBACK=$GEMINI_API_KEY_FALLBACK
GEMINI_API_KEYS=
GEMINI_MODEL=$GEMINI_MODEL
GEMINI_MODEL_PRIORITY=$GEMINI_MODEL,gemini-2.5-flash-lite,gemini-2.0-flash
GEMINI_BASE_URL=https://generativelanguage.googleapis.com
GEMINI_TIMEOUT_SECONDS=45
GEMINI_MAX_RETRIES=2
GEMINI_RETRY_BASE_SECONDS=1.0

# ==== DATA CLEANING ====
DATA_CLEANING_LLM_PROVIDER=mistral
DATA_CLEANING_LLM_ENABLED=$DATA_CLEANING_LLM_ENABLED
MISTRAL_API_KEY=$MISTRAL_API_KEY
MISTRAL_MODEL=$MISTRAL_MODEL
MISTRAL_TIMEOUT_SECONDS=45
MISTRAL_MAX_RETRIES=2
MISTRAL_RETRY_BASE_SECONDS=1.0

# ==== SHARED ====
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
"@

    Set-Content -Path $EnvPath -Value $content
    Write-Host "Fichier .env cree: $EnvPath" -ForegroundColor Green
}

function Update-CorsOnly {
    param([string]$EnvPath)

    $content = Get-Content $EnvPath
    $content = $content -replace '^ALLOWED_ORIGINS=.*', "ALLOWED_ORIGINS=*"
    Set-Content -Path $EnvPath -Value $content
    Write-Host "CORS defini a *" -ForegroundColor Green
}

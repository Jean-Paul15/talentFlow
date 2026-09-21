#!/bin/bash
# Module: Generateur .env officiel

generate_random_secret() {
    openssl rand -base64 32 | tr -d '\n'
}

prompt_with_default() {
    local prompt="$1"
    local default="$2"
    local value
    read -r -p "$prompt [$default]: " value
    echo "${value:-$default}"
}

create_env_file() {
    local env_path="$1"

    JWT_SECRET="$(generate_random_secret)"
    POSTGRES_PASSWORD="$(generate_random_secret)"
    MINIO_ROOT_USER="talentflow_$(openssl rand -hex 4)"
    MINIO_ROOT_PASSWORD="$(generate_random_secret)"
    GRAFANA_PASSWORD="$(generate_random_secret)"

    echo "Configuration Recommendation (Gemini -> DeepSeek)"
    GEMINI_API_KEY="$(prompt_with_default "Gemini API Key principale" "")"
    GEMINI_API_KEY_FALLBACK="$(prompt_with_default "Gemini API Key secondaire" "")"
    GEMINI_MODEL="$(prompt_with_default "Gemini model" "gemini-2.5-flash")"
    DEEPSEEK_API_KEY="$(prompt_with_default "DeepSeek API Key fallback" "")"
    DEEPSEEK_MODEL="$(prompt_with_default "DeepSeek model" "deepseek-chat")"
    echo ""
    echo "Configuration Data-cleaning (Mistral)"
    MISTRAL_API_KEY="$(prompt_with_default "Mistral API Key" "")"
    MISTRAL_MODEL="$(prompt_with_default "Mistral model" "mistral-small-latest")"
    DATA_CLEANING_LLM_ENABLED="$(prompt_with_default "Activer le LLM de nettoyage ? (true/false)" "false")"

    cat > "$env_path" << EOF
# TalentFlow Environment Configuration
# Genere automatiquement le $(date)
JWT_SECRET=$JWT_SECRET
POSTGRES_PASSWORD=$POSTGRES_PASSWORD
MINIO_ROOT_USER=$MINIO_ROOT_USER
MINIO_ROOT_PASSWORD=$MINIO_ROOT_PASSWORD
GRAFANA_PASSWORD=$GRAFANA_PASSWORD
LLM_PROVIDER=gemini
LLM_PROVIDER_ORDER=gemini,deepseek
LLM_FALLBACK_PROVIDER=deepseek
GEMINI_API_KEY=$GEMINI_API_KEY
GEMINI_API_KEY_FALLBACK=$GEMINI_API_KEY_FALLBACK
GEMINI_API_KEYS=
GEMINI_MODEL=$GEMINI_MODEL
GEMINI_MODEL_PRIORITY=$GEMINI_MODEL,gemini-2.5-flash-lite,gemini-2.0-flash
GEMINI_BASE_URL=https://generativelanguage.googleapis.com
GEMINI_TIMEOUT_SECONDS=45
GEMINI_MAX_RETRIES=2
GEMINI_RETRY_BASE_SECONDS=1.0
DEEPSEEK_ENABLED=true
DEEPSEEK_API_KEY=$DEEPSEEK_API_KEY
DEEPSEEK_BASE_URL=https://api.deepseek.com
DEEPSEEK_MODEL=$DEEPSEEK_MODEL
DEEPSEEK_TIMEOUT_SECONDS=45
DEEPSEEK_MAX_RETRIES=2
DEEPSEEK_RETRY_BASE_SECONDS=1.0
DATA_CLEANING_LLM_PROVIDER=mistral
DATA_CLEANING_LLM_ENABLED=$DATA_CLEANING_LLM_ENABLED
MISTRAL_API_KEY=$MISTRAL_API_KEY
MISTRAL_MODEL=$MISTRAL_MODEL
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
EOF

    echo "Fichier .env cree: $env_path"
}

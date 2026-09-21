#!/bin/bash
# Configuration LLM officielle:
# - Recommendation: Gemini -> DeepSeek -> fallback deterministe
# - Data-cleaning: Mistral, puis NER + patterns en fallback

set_llm_provider() {
    local env_path="$1"

    echo "Configuration LLM Provider"
    echo "========================="
    echo "Recommendation: Gemini -> DeepSeek -> fallback deterministe"
    echo "Data-cleaning : Mistral cloud + fallback NER/patterns"
    echo ""

    GEMINI_API_KEY=$(prompt_with_default "  Gemini API Key principale" "")
    GEMINI_API_KEY_FALLBACK=$(prompt_with_default "  Gemini API Key secondaire" "")
    GEMINI_MODEL=$(prompt_with_default "  Gemini model" "gemini-2.5-flash")
    MISTRAL_API_KEY=$(prompt_with_default "  Mistral API Key (data-cleaning)" "")
    MISTRAL_MODEL=$(prompt_with_default "  Mistral model" "mistral-small-latest")

    echo ""
    echo "Configuration LLM:"
    echo "  Recommendation provider: gemini puis deepseek si besoin ($GEMINI_MODEL)"
    echo "  Data-cleaning provider: mistral ($MISTRAL_MODEL)"
    echo "  Cleaning fallback: NER + patterns"
    echo ""
}

append_llm_config_to_env() {
    local env_path="$1"

    cat >> "$env_path" << 'EOF'

# ==== LLM CONFIGURATION ====
LLM_PROVIDER=gemini
LLM_PROVIDER_ORDER=gemini,deepseek
LLM_FALLBACK_PROVIDER=deepseek
GEMINI_API_KEY=
GEMINI_API_KEY_FALLBACK=
GEMINI_API_KEYS=
GEMINI_MODEL=gemini-2.5-flash
GEMINI_MODEL_PRIORITY=gemini-2.5-flash,gemini-2.5-flash-lite,gemini-2.0-flash
GEMINI_BASE_URL=https://generativelanguage.googleapis.com
GEMINI_TIMEOUT_SECONDS=45
GEMINI_MAX_RETRIES=2
GEMINI_RETRY_BASE_SECONDS=1.0
DEEPSEEK_ENABLED=true
DEEPSEEK_API_KEY=
DEEPSEEK_BASE_URL=https://api.deepseek.com
DEEPSEEK_MODEL=deepseek-chat
DEEPSEEK_TIMEOUT_SECONDS=45
DEEPSEEK_MAX_RETRIES=2
DEEPSEEK_RETRY_BASE_SECONDS=1.0
LLM_TEMPERATURE=0.3

# ==== DATA CLEANING LLM ====
DATA_CLEANING_LLM_PROVIDER=mistral
DATA_CLEANING_LLM_ENABLED=false
MISTRAL_API_KEY=
MISTRAL_MODEL=mistral-small-latest
MISTRAL_TIMEOUT_SECONDS=45
MISTRAL_MAX_RETRIES=2
MISTRAL_RETRY_BASE_SECONDS=1.0
EOF
}

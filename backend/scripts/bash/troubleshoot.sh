#!/bin/bash
# Diagnostic rapide LLM / runtime TalentFlow

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

issues=0

issue() {
    echo -e "${RED}[ISSUE]${NC} $1"
    ((issues++))
}

info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

debug() {
    echo -e "${YELLOW}[DEBUG]${NC} $1"
}

echo -e "${BLUE}=== TALENTFLOW TROUBLESHOOTING TOOL ===${NC}"

if [ ! -f ".env" ]; then
    issue "Fichier .env manquant"
else
    if grep -q "^LLM_PROVIDER=gemini" .env; then
        info "Recommendation provider: gemini"
    else
        issue "LLM_PROVIDER doit valoir gemini"
    fi

    if grep -q "^GEMINI_API_KEY=." .env; then
        info "Gemini API key principale configuree"
    else
        issue "Gemini API key principale manquante"
    fi

    if grep -q "^DATA_CLEANING_LLM_PROVIDER=mistral" .env; then
        info "Data-cleaning provider: mistral"
    else
        issue "DATA_CLEANING_LLM_PROVIDER doit valoir mistral"
    fi

    if grep -q "^DATA_CLEANING_LLM_ENABLED=true" .env; then
        if grep -q "^MISTRAL_API_KEY=." .env; then
            info "Mistral API key configuree"
        else
            issue "Mistral API key manquante alors que DATA_CLEANING_LLM_ENABLED=true"
        fi
    else
        debug "Data-cleaning LLM desactive (tolere)"
    fi

fi

if docker compose -f backend/docker-compose.yml config >/dev/null 2>&1; then
    info "docker compose config standard OK"
else
    issue "docker compose config standard en echec"
fi

if [ "$issues" -eq 0 ]; then
    echo -e "${GREEN}Aucun probleme detecte${NC}"
    exit 0
fi

echo -e "${RED}$issues probleme(s) detecte(s)${NC}"
exit 1

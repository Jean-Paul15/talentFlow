#!/bin/bash
# Deploy Checklist - Vérifications avant production TalentFlow
# Usage: ./scripts/bash/deploy-checklist.sh

set -e

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

echo -e "${BLUE}=== TALENTFLOW DEPLOYMENT CHECKLIST ===${NC}\n"

# Compteur
CHECKS_PASSED=0
CHECKS_FAILED=0
CHECKS_WARNING=0

# Fonction pour vérifier
check_pass() {
    echo -e "${GREEN}[PASS]${NC} $1"
    ((CHECKS_PASSED++))
}

check_fail() {
    echo -e "${RED}[FAIL]${NC} $1"
    ((CHECKS_FAILED++))
}

check_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
    ((CHECKS_WARNING++))
}

# 1. VÉRIFICATIONS FICHIERS
echo -e "${BLUE}1. FICHIERS CONFIGURATION${NC}"

if [ -f ".env" ]; then
    check_pass "Fichier .env existe"
else
    check_fail "Fichier .env MANQUANT"
fi

if [ -f "docker-compose.yml" ]; then
    check_pass "docker-compose.yml existe"
else
    check_fail "docker-compose.yml MANQUANT"
fi

if [ -d "recommendation" ]; then
    check_pass "Dossier recommendation existe"
else
    check_fail "Dossier recommendation MANQUANT"
fi

# 2. VARIABLES ENVIRONNEMENT
echo -e "\n${BLUE}2. VARIABLES ENVIRONNEMENT${NC}"

if [ -f ".env" ]; then
    if grep -q "LLM_PROVIDER=" .env; then
        LLM=$(grep "LLM_PROVIDER=" .env | cut -d= -f2)
        check_pass "LLM_PROVIDER défini: $LLM"
    else
        check_fail "LLM_PROVIDER non défini dans .env"
    fi
    
    if grep -q "POSTGRES_PASSWORD=" .env; then
        check_pass "POSTGRES_PASSWORD défini"
    else
        check_fail "POSTGRES_PASSWORD non défini"
    fi
    
    if grep -q "JWT_SECRET=" .env; then
        check_pass "JWT_SECRET défini"
    else
        check_fail "JWT_SECRET non défini"
    fi
    
    if grep -q "REDIS_HOST=" .env; then
        REDIS_HOST=$(grep "REDIS_HOST=" .env | cut -d= -f2)
        check_pass "REDIS_HOST défini: $REDIS_HOST"
    else
        check_fail "REDIS_HOST non défini"
    fi
else
    check_warn "Impossible de vérifier .env (fichier absent)"
fi

# 3. SERVICES DOCKER
echo -e "\n${BLUE}3. SERVICES DOCKER${NC}"

if command -v docker &> /dev/null; then
    check_pass "Docker installé"
    
    if command -v docker-compose &> /dev/null || docker compose version &> /dev/null; then
        check_pass "Docker Compose installé"
    else
        check_fail "Docker Compose NOT installed"
    fi
else
    check_fail "Docker NOT installed"
fi

# 4. DÉPENDANCES PYTHON
echo -e "\n${BLUE}4. DÉPENDANCES PYTHON${NC}"

if command -v python3 &> /dev/null; then
    PYTHON_VERSION=$(python3 --version | cut -d' ' -f2)
    check_pass "Python 3 installé: $PYTHON_VERSION"
    
    if python3 -c "import fastapi" 2>/dev/null; then
        check_pass "FastAPI disponible"
    else
        check_warn "FastAPI non installé (installer: pip install fastapi)"
    fi
    
    if python3 -c "import langchain" 2>/dev/null; then
        check_pass "LangChain disponible"
    else
        check_warn "LangChain non installé (installer: pip install langchain)"
    fi
    
    if python3 -c "import redis" 2>/dev/null; then
        check_pass "Redis-py disponible"
    else
        check_warn "Redis-py non installé (installer: pip install redis)"
    fi
else
    check_fail "Python 3 NOT installed"
fi

# 5. PORTS DISPONIBLES
echo -e "\n${BLUE}5. PORTS DISPONIBLES${NC}"

check_port() {
    if nc -z localhost $1 2>/dev/null; then
        check_warn "Port $1 est OCCUPÉ (service peut déjà tourner)"
    else
        check_pass "Port $1 est libre"
    fi
}

if command -v nc &> /dev/null; then
    check_port 3000  # API Gateway
    check_port 8000  # Job Sourcing
    check_port 8001  # Recommendation
    check_port 5432  # PostgreSQL
    check_port 6379  # Redis
else
    check_warn "netcat non disponible (skip vérification ports)"
fi

# 6. SÉCURITÉ
echo -e "\n${BLUE}6. SÉCURITÉ${NC}"

if [ -f ".env" ]; then
    if grep -q "ALLOWED_ORIGINS=\*" .env; then
        check_warn "ALLOWED_ORIGINS='*' - OK pour DEV, restreindre en PROD"
    else
        check_pass "ALLOWED_ORIGINS restreint"
    fi
    
    if ! grep -q "SECRET_KEY=" .env && ! grep -q "JWT_SECRET=" .env; then
        check_warn "Pas de SECRET défini"
    else
        check_pass "SECRET défini"
    fi
else
    check_warn "Impossible de vérifier sécurité"
fi

# 7. RÉSUMÉ
echo -e "\n${BLUE}========== RÉSUMÉ ==========${NC}"
echo -e "${GREEN}Passed:${NC}  $CHECKS_PASSED"
echo -e "${YELLOW}Warning:${NC} $CHECKS_WARNING"
echo -e "${RED}Failed:${NC}  $CHECKS_FAILED"

if [ $CHECKS_FAILED -eq 0 ]; then
    echo -e "\n${GREEN}Prêt pour déploiement!${NC}"
    exit 0
else
    echo -e "\n${RED}Corriger les erreurs avant déploiement${NC}"
    exit 1
fi

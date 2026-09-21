#!/bin/bash
# Quick Start Script - Demarrage rapide TalentFlow en 3 commandes
# Usage: ./scripts/bash/quick-start.sh

set -e

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

echo -e "${BLUE}"
echo "╔════════════════════════════════════════════╗"
echo "║  TALENTFLOW QUICK START                    ║"
echo "║  Démarrage rapide en 3 étapes              ║"
echo "╚════════════════════════════════════════════╝"
echo -e "${NC}"

# ÉTAPE 1: Vérifications
echo -e "\n${BLUE}ÉTAPE 1: Vérifications préalables...${NC}"

if ! command -v docker &> /dev/null; then
    echo -e "${RED}Erreur: Docker n'est pas installé${NC}"
    echo "Installer depuis: https://docs.docker.com/engine/install/"
    exit 1
fi

if ! command -v docker-compose &> /dev/null && ! docker compose version &> /dev/null 2>&1; then
    echo -e "${RED}Erreur: Docker Compose n'est pas installé${NC}"
    exit 1
fi

echo -e "${GREEN}✓ Docker et Docker Compose détectés${NC}"

# ÉTAPE 2: Configuration .env
echo -e "\n${BLUE}ÉTAPE 2: Configuration (.env)...${NC}"

if [ -f ".env" ]; then
    echo -e "${YELLOW}Le fichier .env existe déjà${NC}"
    read -p "Voulez-vous le régénérer? (o/n) " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Oo]$ ]]; then
        rm .env
    else
        echo -e "${GREEN}✓ Utilisation du .env existant${NC}"
    fi
fi

if [ ! -f ".env" ]; then
    echo -e "${YELLOW}Génération du fichier .env...${NC}"
    
    if [ -f "scripts/python/env-generator.py" ]; then
        python3 scripts/python/env-generator.py
    elif [ -f "scripts/powershell/env-generator-clean.ps1" ]; then
        echo "Utiliser: pwsh scripts/powershell/env-generator-clean.ps1"
        read -p "Appuyer sur Entrée après génération du .env"
    else
        echo -e "${RED}Erreur: Script env-generator non trouvé${NC}"
        exit 1
    fi
    
    echo -e "${GREEN}✓ Fichier .env créé${NC}"
fi

# ÉTAPE 3: Démarrage services
echo -e "\n${BLUE}ÉTAPE 3: Démarrage des services...${NC}"

if [ ! -f "docker-compose.yml" ]; then
    echo -e "${RED}Erreur: docker-compose.yml non trouvé${NC}"
    exit 1
fi

echo "Démarrage des containers..."
docker-compose up -d

# Attendre que services soient prêts
echo -e "\n${YELLOW}Attendre initialisation des services...${NC}"
sleep 5

# Vérifier que services tournent
if docker-compose ps --services --filter "status=running" | grep -q .; then
    echo -e "${GREEN}✓ Services démarrés${NC}"
else
    echo -e "${RED}Erreur: Certains services n'ont pas démarré${NC}"
    echo "Consulter: docker-compose logs"
    exit 1
fi

# ÉTAPE 4: Vérifications finales
echo -e "\n${BLUE}ÉTAPE 4: Vérifications finales...${NC}"

# Vérifier PostgreSQL
if docker-compose exec -T postgres pg_isready -U talentflow &>/dev/null; then
    echo -e "${GREEN}✓ PostgreSQL est prêt${NC}"
else
    echo -e "${YELLOW}⚠ PostgreSQL en cours d'initialisation...${NC}"
fi

# Vérifier Redis
if docker-compose exec -T redis redis-cli ping &>/dev/null | grep -q PONG; then
    echo -e "${GREEN}✓ Redis est prêt${NC}"
fi

# Vérifier ports
sleep 3
if curl -s http://localhost:3000/health &>/dev/null; then
    echo -e "${GREEN}✓ API Gateway (3000) répond${NC}"
fi

if curl -s http://localhost:8001/health &>/dev/null; then
    echo -e "${GREEN}✓ Recommendation Service (8001) répond${NC}"
fi

# RÉSUMÉ FINAL
echo -e "\n${BLUE}════════════════════════════════════════════${NC}"
echo -e "${GREEN}DÉMARRAGE COMPLÉTÉ!${NC}"
echo -e "${BLUE}════════════════════════════════════════════${NC}\n"

echo "Services disponibles:"
echo -e "  ${GREEN}API Gateway${NC}           http://localhost:3000"
echo -e "  ${GREEN}Recommendation Service${NC}  http://localhost:8001"
echo -e "  ${GREEN}Job Sourcing Service${NC}    http://localhost:8000"
echo -e "  ${GREEN}PostgreSQL${NC}             localhost:5432"
echo -e "  ${GREEN}Redis${NC}                  localhost:6379"

echo -e "\nCommandes utiles:"
echo "  Voir logs:           ${YELLOW}docker-compose logs -f${NC}"
echo "  Arrêter services:    ${YELLOW}docker-compose down${NC}"
echo "  Diagnostic:          ${YELLOW}./scripts/bash/troubleshoot.sh${NC}"
echo "  Deploy checklist:    ${YELLOW}./scripts/bash/deploy-checklist.sh${NC}"

echo -e "\n${GREEN}Prêt pour développement/test!${NC}\n"

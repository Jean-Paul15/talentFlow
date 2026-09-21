#!/bin/bash
# TalentFlow - Script de gestion unifié
# Usage: ./manage.sh [command] [options]

set -e

# Couleurs
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Répertoire du script
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$SCRIPT_DIR"

# Charger modules
source "$SCRIPT_DIR/scripts/bash/env-generator.sh"
source "$SCRIPT_DIR/scripts/bash/service-manager.sh"
source "$SCRIPT_DIR/scripts/bash/docker-ops.sh"
source "$SCRIPT_DIR/scripts/bash/auto-orchestrator.sh"

# Banner
show_banner() {
    echo -e "${BLUE}"
    echo "╔════════════════════════════════════════╗"
    echo "║       TalentFlow Management CLI        ║"
    echo "║     Gestion Automatisée Backend        ║"
    echo "╚════════════════════════════════════════╝"
    echo -e "${NC}"
}

# Aide
show_help() {
    cat << EOF
${GREEN}Usage:${NC}
  ./manage.sh [command] [service] [options]

${GREEN}Commands:${NC}
  ${YELLOW}init${NC}              Initialisation complète (env + docker)
  ${YELLOW}start${NC} [service]   Démarrer service(s)
  ${YELLOW}stop${NC} [service]    Arrêter service(s)
  ${YELLOW}restart${NC} [service] Redémarrer service(s)
  ${YELLOW}rebuild${NC} [service] Rebuild + démarrer service(s)
  ${YELLOW}logs${NC} [service]    Voir logs (-f pour follow)
  ${YELLOW}status${NC}            Status tous services
  ${YELLOW}health${NC}            Health check API
  ${YELLOW}env${NC}               Créer/régénérer .env
  ${YELLOW}cors${NC}              Régénérer CORS uniquement
  ${YELLOW}backup${NC}            Backup volumes Docker
  ${YELLOW}restore${NC} <dir>     Restaurer volumes
  ${YELLOW}prune${NC}             Nettoyage Docker
  ${YELLOW}scale${NC} <svc> <n>   Scaler service à n instances
  ${YELLOW}auto${NC} <mode> [opts] Orchestration intelligente on-demand

${GREEN}Services disponibles:${NC}
  - api-gateway
  - job-sourcing
  - recommendation
  - data-cleaning
  - search-engine
  - postgres
  - redis
  - elasticsearch
  - minio
  - mongodb

${GREEN}Exemples:${NC}
  ./manage.sh init                  # Setup complet
  ./manage.sh start                 # Démarre tout
  ./manage.sh start recommendation  # Démarre service spécifique
  ./manage.sh rebuild api-gateway   # Rebuild + redémarre
  ./manage.sh logs job-sourcing -f  # Logs en temps réel
  ./manage.sh cors                  # Régénère CORS (*  dev)
  ./manage.sh scale search-engine 3 # 3 instances search
  ./manage.sh auto api              # start minimal API
  ./manage.sh auto sourcing-full trim # start sourcing + trim inutile
  ./manage.sh auto status           # modes + services actifs

EOF
}

# Vérification .env
check_env() {
    if [ ! -f "$PROJECT_ROOT/.env" ]; then
        echo -e "${YELLOW}⚠️  Fichier .env manquant${NC}"
        echo ""
        read -p "Créer automatiquement? [Y/n]: " create_env
        
        if [ "$create_env" != "n" ] && [ "$create_env" != "N" ]; then
            create_env_file "$PROJECT_ROOT/.env"
        else
            echo -e "${RED}❌ .env requis pour continuer${NC}"
            exit 1
        fi
    fi
}

# Init projet complet
init_project() {
    show_banner
    echo -e "${BLUE}🔧 Initialisation TalentFlow${NC}"
    echo ""
    
    # 1. Créer .env si manquant
    if [ ! -f "$PROJECT_ROOT/.env" ]; then
        create_env_file "$PROJECT_ROOT/.env"
    else
        echo "ℹ️  .env déjà existant (skip)"
    fi
    
    # 2. Créer réseau Docker
    create_network
    
    # 3. Créer dossiers requis
    echo ""
    echo "📁 Création structure dossiers..."
    mkdir -p logs backups
    mkdir -p /var/log/talentflow 2>/dev/null || true
    
    # 4. Build images
    echo ""
    echo "🏗️  Build images Docker..."
    docker-compose build
    
    # 5. Démarrer services
    echo ""
    echo "🚀 Démarrage services..."
    docker-compose up -d
    
    # 6. Attendre services
    echo ""
    echo "⏳ Attente démarrage services (30s)..."
    sleep 30
    
    # 7. Health check
    echo ""
    health_check
    
    echo ""
    echo -e "${GREEN}✅ Initialisation terminée!${NC}"
    echo ""
    echo "🌍 Accès services:"
    echo "  - API Gateway: http://localhost:3000"
    echo "  - Grafana: http://localhost:3001 (admin / <voir .env>)"
    echo "  - Airflow: http://localhost:8080"
    echo "  - MinIO Console: http://localhost:9001"
    echo ""
}

# Main
main() {
    cd "$PROJECT_ROOT"
    
    case "$1" in
        init)
            init_project
            ;;
        start)
            check_env
            start_service "$2"
            ;;
        stop)
            stop_service "$2"
            ;;
        restart)
            check_env
            restart_service "$2"
            ;;
        rebuild)
            check_env
            rebuild_service "$2"
            ;;
        logs)
            if [ "$3" = "-f" ]; then
                logs_service "$2" "true"
            else
                logs_service "$2" "false"
            fi
            ;;
        status)
            status_services
            ;;
        health)
            health_check
            ;;
        env)
            create_env_file "$PROJECT_ROOT/.env"
            ;;
        cors)
            if [ ! -f "$PROJECT_ROOT/.env" ]; then
                echo -e "${RED}❌ .env n'existe pas${NC}"
                exit 1
            fi
            regenerate_cors_only "$PROJECT_ROOT/.env"
            ;;
        backup)
            backup_volumes
            ;;
        restore)
            restore_volumes "$2"
            ;;
        prune)
            prune_docker
            ;;
        scale)
            scale_service "$2" "$3"
            ;;
        auto)
            auto_orchestrate "$2" "$3"
            ;;
        help|--help|-h|"")
            show_help
            ;;
        *)
            echo -e "${RED}❌ Commande inconnue: $1${NC}"
            echo ""
            show_help
            exit 1
            ;;
    esac
}

# Exécution
main "$@"

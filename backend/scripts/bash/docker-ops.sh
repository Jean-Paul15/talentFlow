#!/bin/bash
# Module: Opérations Docker avancées

prune_docker() {
    echo "🧹 Nettoyage Docker..."
    echo ""
    
    read -p "⚠️  Supprimer containers arrêtés, images non utilisées, volumes? [y/N]: " confirm
    
    if [ "$confirm" = "y" ] || [ "$confirm" = "Y" ]; then
        docker system prune -a --volumes -f
        echo "✅ Nettoyage terminé"
    else
        echo "❌ Annulé"
    fi
}

backup_volumes() {
    local backup_dir="./backups/$(date +%Y%m%d_%H%M%S)"
    
    echo "💾 Backup des volumes Docker..."
    mkdir -p "$backup_dir"
    
    volumes=(
        "postgres_data"
        "mongodb_data"
        "minio_data"
        "grafana_data"
    )
    
    for volume in "${volumes[@]}"; do
        echo "  Backup $volume..."
        docker run --rm \
            -v "${volume}:/data" \
            -v "$(pwd)/$backup_dir:/backup" \
            alpine tar czf "/backup/${volume}.tar.gz" -C /data .
    done
    
    echo "✅ Backups créés dans $backup_dir"
}

restore_volumes() {
    local backup_dir="$1"
    
    if [ -z "$backup_dir" ]; then
        echo "❌ Usage: restore_volumes <backup_dir>"
        return 1
    fi
    
    echo "♻️  Restauration depuis $backup_dir..."
    
    read -p "⚠️  Ceci écrasera les données actuelles. Continuer? [y/N]: " confirm
    
    if [ "$confirm" != "y" ] && [ "$confirm" != "Y" ]; then
        echo "❌ Annulé"
        return 1
    fi
    
    for archive in "$backup_dir"/*.tar.gz; do
        volume=$(basename "$archive" .tar.gz)
        echo "  Restauration $volume..."
        
        docker run --rm \
            -v "${volume}:/data" \
            -v "$(pwd)/$backup_dir:/backup" \
            alpine sh -c "rm -rf /data/* && tar xzf /backup/${volume}.tar.gz -C /data"
    done
    
    echo "✅ Restauration terminée"
}

create_network() {
    if ! docker network inspect talentflow_network > /dev/null 2>&1; then
        echo "🌐 Création réseau talentflow_network..."
        docker network create talentflow_network
        echo "✅ Réseau créé"
    else
        echo "ℹ️  Réseau talentflow_network déjà existant"
    fi
}

scale_service() {
    local service_name="$1"
    local replicas="$2"
    
    if [ -z "$service_name" ] || [ -z "$replicas" ]; then
        echo "❌ Usage: scale_service <service> <replicas>"
        return 1
    fi
    
    echo "📈 Scaling $service_name à $replicas instances..."
    docker-compose up -d --scale "$service_name=$replicas"
    echo "✅ Service scalé"
}

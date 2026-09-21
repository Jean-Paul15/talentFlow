#!/bin/bash
# Module: Gestion services Docker

start_service() {
    local service_name="$1"
    
    if [ -z "$service_name" ]; then
        echo "🚀 Démarrage de TOUS les services..."
        docker-compose up -d
    else
        echo "🚀 Démarrage de $service_name..."
        docker-compose up -d "$service_name"
    fi
    
    echo "✅ Service(s) démarré(s)"
}

stop_service() {
    local service_name="$1"
    
    if [ -z "$service_name" ]; then
        echo "🛑 Arrêt de TOUS les services..."
        docker-compose down
    else
        echo "🛑 Arrêt de $service_name..."
        docker-compose stop "$service_name"
    fi
    
    echo "✅ Service(s) arrêté(s)"
}

restart_service() {
    local service_name="$1"
    
    echo "🔄 Redémarrage..."
    stop_service "$service_name"
    sleep 2
    start_service "$service_name"
}

rebuild_service() {
    local service_name="$1"
    
    if [ -z "$service_name" ]; then
        echo "🔨 Rebuild de TOUS les services..."
        docker-compose build
        docker-compose up -d
    else
        echo "🔨 Rebuild de $service_name..."
        docker-compose build "$service_name"
        docker-compose up -d "$service_name"
    fi
    
    echo "✅ Service(s) rebuild et démarré(s)"
}

logs_service() {
    local service_name="$1"
    local follow="${2:-false}"
    
    if [ "$follow" = "true" ]; then
        if [ -z "$service_name" ]; then
            docker-compose logs -f
        else
            docker-compose logs -f "$service_name"
        fi
    else
        if [ -z "$service_name" ]; then
            docker-compose logs --tail=100
        else
            docker-compose logs --tail=100 "$service_name"
        fi
    fi
}

status_services() {
    echo "📊 Status des services TalentFlow:"
    echo ""
    docker-compose ps
}

health_check() {
    echo "🏥 Vérification santé des services..."
    echo ""
    
    services=(
        "api-gateway:3000"
        "job-sourcing:8000"
        "recommendation:8001"
        "data-cleaning:8002"
        "search-engine:8003"
    )
    
    for service in "${services[@]}"; do
        IFS=':' read -r name port <<< "$service"
        
        if curl -sf "http://localhost:$port/health" > /dev/null 2>&1; then
            echo "✅ $name (port $port): HEALTHY"
        else
            echo "❌ $name (port $port): UNHEALTHY"
        fi
    done
}

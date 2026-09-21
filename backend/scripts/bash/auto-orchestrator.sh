#!/bin/bash
# Smart orchestrator for Docker services (on-demand start/stop)

declare -A AUTO_MODE_ENTRY
AUTO_MODE_ENTRY["sourcing-lite"]="job-sourcing spark-streaming lake-api"
AUTO_MODE_ENTRY["sourcing-full"]="job-sourcing spark-streaming data-cleaning lake-api"
AUTO_MODE_ENTRY["pipeline"]="job-sourcing spark-streaming data-cleaning search-engine recommendation"
AUTO_MODE_ENTRY["search"]="search-engine"
AUTO_MODE_ENTRY["recommendation"]="recommendation"
AUTO_MODE_ENTRY["api"]="api-gateway"
AUTO_MODE_ENTRY["dashboard"]="streamlit"
AUTO_MODE_ENTRY["lake-only"]="lake-api streamlit"
AUTO_MODE_ENTRY["orchestration"]="airflow"
AUTO_MODE_ENTRY["monitoring"]="prometheus grafana"
AUTO_MODE_ENTRY["all"]="api-gateway streamlit airflow prometheus grafana job-sourcing data-cleaning spark-streaming"

declare -A SERVICE_DEPS
SERVICE_DEPS["api-gateway"]="postgres redis search-engine recommendation"
SERVICE_DEPS["recommendation"]="search-engine redis"
SERVICE_DEPS["search-engine"]="mongodb qdrant"
SERVICE_DEPS["streamlit"]="lake-api minio"
SERVICE_DEPS["lake-api"]="minio"
SERVICE_DEPS["job-sourcing"]="minio redis kafka"
SERVICE_DEPS["spark-streaming"]="kafka minio"
SERVICE_DEPS["data-cleaning"]="minio mongodb"
SERVICE_DEPS["airflow"]="postgres kafka"
SERVICE_DEPS["kafka"]="zookeeper"
SERVICE_DEPS["grafana"]="prometheus"

declare -A MODE_HEALTH
MODE_HEALTH["sourcing-lite"]="job-sourcing|http://localhost:8000/health lake-api|http://localhost:8004/health"
MODE_HEALTH["sourcing-full"]="job-sourcing|http://localhost:8000/health data-cleaning|http://localhost:8002/health lake-api|http://localhost:8004/health"
MODE_HEALTH["pipeline"]="job-sourcing|http://localhost:8000/health data-cleaning|http://localhost:8002/health search-engine|http://localhost:8003/health recommendation|http://localhost:8001/health"
MODE_HEALTH["search"]="search-engine|http://localhost:8003/health"
MODE_HEALTH["recommendation"]="recommendation|http://localhost:8001/health"
MODE_HEALTH["api"]="api-gateway|http://localhost:3000/health"
MODE_HEALTH["dashboard"]="streamlit|http://localhost:8501/_stcore/health"
MODE_HEALTH["lake-only"]="streamlit|http://localhost:8501/_stcore/health lake-api|http://localhost:8004/health"
MODE_HEALTH["orchestration"]="airflow|http://localhost:8080/health"
MODE_HEALTH["monitoring"]="prometheus|http://localhost:9090/-/healthy grafana|http://localhost:3001/api/health"

list_auto_modes() {
    for k in "${!AUTO_MODE_ENTRY[@]}"; do
        echo "$k"
    done | sort
}

running_services() {
    docker-compose ps --services --filter "status=running" 2>/dev/null | sed '/^\s*$/d'
}

expand_service_set() {
    local queue=("$@")
    local out=()
    local seen_str=" "
    while [ ${#queue[@]} -gt 0 ]; do
        local svc="${queue[0]}"
        queue=("${queue[@]:1}")
        [ -z "$svc" ] && continue
        if [[ "$seen_str" == *" $svc "* ]]; then
            continue
        fi
        seen_str+=" $svc "
        out+=("$svc")
        if [ -n "${SERVICE_DEPS[$svc]}" ]; then
            # shellcheck disable=SC2206
            local deps=( ${SERVICE_DEPS[$svc]} )
            queue+=("${deps[@]}")
        fi
    done
    echo "${out[*]}"
}

resolve_mode_services() {
    local modes=("$@")
    local entries=()
    local mode
    for mode in "${modes[@]}"; do
        if [ -z "${AUTO_MODE_ENTRY[$mode]}" ]; then
            echo "ERROR: unknown mode '$mode'" >&2
            return 1
        fi
        # shellcheck disable=SC2206
        local svcs=( ${AUTO_MODE_ENTRY[$mode]} )
        entries+=("${svcs[@]}")
    done
    expand_service_set "${entries[@]}"
}

endpoint_ready() {
    local url="$1"
    local timeout="${2:-120}"
    local start_ts
    start_ts="$(date +%s)"
    while true; do
        if curl -fsS --max-time 4 "$url" >/dev/null 2>&1; then
            return 0
        fi
        local now_ts
        now_ts="$(date +%s)"
        if [ $((now_ts - start_ts)) -ge "$timeout" ]; then
            return 1
        fi
        sleep 2
    done
}

wait_mode_health() {
    local timeout_per_check="${1:-120}"
    shift
    local modes=("$@")
    local checks=()
    local mode
    for mode in "${modes[@]}"; do
        if [ -n "${MODE_HEALTH[$mode]}" ]; then
            # shellcheck disable=SC2206
            local mode_checks=( ${MODE_HEALTH[$mode]} )
            checks+=("${mode_checks[@]}")
        fi
    done
    local seen_urls=" "
    local pair
    for pair in "${checks[@]}"; do
        local name="${pair%%|*}"
        local url="${pair#*|}"
        if [[ "$seen_urls" == *" $url "* ]]; then
            continue
        fi
        seen_urls+=" $url "
        if endpoint_ready "$url" "$timeout_per_check"; then
            echo "✅ $name ready ($url)"
        else
            echo "⚠️  $name not ready ($url)"
        fi
    done
}

auto_status() {
    echo "Modes disponibles: $(list_auto_modes | tr '\n' ' ' | sed 's/ $//')"
    local running
    running="$(running_services)"
    if [ -z "$running" ]; then
        echo "Aucun service en cours."
        return 0
    fi
    echo "Services en cours: $(echo "$running" | tr '\n' ' ' | sed 's/ $//')"
}

auto_orchestrate() {
    local mode="$1"
    local options="${2:-}"
    mode="$(echo "$mode" | tr '[:upper:]' '[:lower:]' | xargs)"

    if [ "$mode" = "status" ] || [ "$mode" = "list" ] || [ "$mode" = "modes" ] || [ -z "$mode" ]; then
        auto_status
        return 0
    fi

    local mode_norm
    mode_norm="$(echo "$mode" | tr '+' ',' )"
    IFS=',' read -r -a modes <<< "$mode_norm"

    local target_line
    target_line="$(resolve_mode_services "${modes[@]}")" || return 1
    # shellcheck disable=SC2206
    local target=( $target_line )

    local trim="false"
    local down="false"
    local nowait="false"
    local token
    for token in $(echo "$options" | tr ',;' ' '); do
        case "$(echo "$token" | tr '[:upper:]' '[:lower:]')" in
            trim) trim="true" ;;
            down) down="true" ;;
            nowait) nowait="true" ;;
        esac
    done

    local running_line
    running_line="$(running_services)"
    local running=( )
    if [ -n "$running_line" ]; then
        while IFS= read -r line; do
            [ -n "$line" ] && running+=("$line")
        done <<< "$running_line"
    fi

    if [ "$down" = "true" ]; then
        local to_stop=( )
        local svc
        for svc in "${running[@]}"; do
            if [[ " ${target[*]} " == *" $svc "* ]]; then
                to_stop+=("$svc")
            fi
        done
        if [ ${#to_stop[@]} -gt 0 ]; then
            echo "🛑 Stop mode [$mode]: ${to_stop[*]}"
            docker-compose stop "${to_stop[@]}"
        else
            echo "Rien à arrêter pour ce mode."
        fi
        return 0
    fi

    local missing=( )
    local svc
    for svc in "${target[@]}"; do
        if [[ " ${running[*]} " != *" $svc "* ]]; then
            missing+=("$svc")
        fi
    done

    if [ ${#missing[@]} -gt 0 ]; then
        echo "🚀 On-demand start [$mode]: ${missing[*]}"
        docker-compose up -d "${missing[@]}"
    else
        echo "✅ Mode [$mode] déjà prêt (aucun service manquant)."
    fi

    if [ "$trim" = "true" ]; then
        local running_after_line
        running_after_line="$(running_services)"
        local running_after=( )
        if [ -n "$running_after_line" ]; then
            while IFS= read -r line; do
                [ -n "$line" ] && running_after+=("$line")
            done <<< "$running_after_line"
        fi
        local to_stop=( )
        for svc in "${running_after[@]}"; do
            if [[ " ${target[*]} " != *" $svc "* ]]; then
                to_stop+=("$svc")
            fi
        done
        if [ ${#to_stop[@]} -gt 0 ]; then
            echo "🧹 Trim services inutiles: ${to_stop[*]}"
            docker-compose stop "${to_stop[@]}"
        fi
    fi

    if [ "$nowait" != "true" ]; then
        wait_mode_health 120 "${modes[@]}"
    fi
}

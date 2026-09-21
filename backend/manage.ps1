# TalentFlow - Script de gestion unifié (PowerShell)
# Usage: .\manage.ps1 [command] [options]

param(
    [Parameter(Position=0)]
    [string]$Command,
    
    [Parameter(Position=1)]
    [string]$ServiceName,
    
    [Parameter(Position=2)]
    [object]$Extra,
    
    [switch]$Follow
)

# Répertoire du script
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$ProjectRoot = $ScriptDir

# Charger modules
. "$ScriptDir\scripts\powershell\env-generator.ps1"
. "$ScriptDir\scripts\powershell\service-manager.ps1"
. "$ScriptDir\scripts\powershell\docker-ops.ps1"
. "$ScriptDir\scripts\powershell\auto-orchestrator.ps1"

# Banner
function Show-Banner {
    Write-Host ""
    Write-Host "╔════════════════════════════════════════╗" -ForegroundColor Blue
    Write-Host "║       TalentFlow Management CLI        ║" -ForegroundColor Blue
    Write-Host "║     Gestion Automatisée Backend        ║" -ForegroundColor Blue
    Write-Host "╚════════════════════════════════════════╝" -ForegroundColor Blue
    Write-Host ""
}

# Aide
function Show-Help {
    Write-Host "Usage:" -ForegroundColor Green
    Write-Host "  .\manage.ps1 [command] [service] [options]"
    Write-Host ""
    Write-Host "Commands:" -ForegroundColor Green
    Write-Host "  init              " -NoNewline -ForegroundColor Yellow
    Write-Host "Initialisation complète (env + docker)"
    Write-Host "  start [service]   " -NoNewline -ForegroundColor Yellow
    Write-Host "Démarrer service(s)"
    Write-Host "  stop [service]    " -NoNewline -ForegroundColor Yellow
    Write-Host "Arrêter service(s)"
    Write-Host "  restart [service] " -NoNewline -ForegroundColor Yellow
    Write-Host "Redémarrer service(s)"
    Write-Host "  rebuild [service] " -NoNewline -ForegroundColor Yellow
    Write-Host "Rebuild + démarrer service(s)"
    Write-Host "  logs [service]    " -NoNewline -ForegroundColor Yellow
    Write-Host "Voir logs (-Follow pour temps réel)"
    Write-Host "  status            " -NoNewline -ForegroundColor Yellow
    Write-Host "Status tous services"
    Write-Host "  health            " -NoNewline -ForegroundColor Yellow
    Write-Host "Health check API"
    Write-Host "  env               " -NoNewline -ForegroundColor Yellow
    Write-Host "Créer/régénérer .env"
    Write-Host "  cors              " -NoNewline -ForegroundColor Yellow
    Write-Host "Régénérer CORS uniquement"
    Write-Host "  backup            " -NoNewline -ForegroundColor Yellow
    Write-Host "Backup volumes Docker"
    Write-Host "  restore [dir]     " -NoNewline -ForegroundColor Yellow
    Write-Host "Restaurer volumes"
    Write-Host "  prune             " -NoNewline -ForegroundColor Yellow
    Write-Host "Nettoyage Docker"
    Write-Host "  scale [svc] [n]   " -NoNewline -ForegroundColor Yellow
    Write-Host "Scaler service à n instances"
    Write-Host "  auto [mode] [opts]" -NoNewline -ForegroundColor Yellow
    Write-Host "Orchestration intelligente on-demand"
    Write-Host ""
    Write-Host "Services disponibles:" -ForegroundColor Green
    Write-Host "  - api-gateway"
    Write-Host "  - job-sourcing"
    Write-Host "  - recommendation"
    Write-Host "  - data-cleaning"
    Write-Host "  - search-engine"
    Write-Host "  - postgres"
    Write-Host "  - redis"
    Write-Host "  - elasticsearch"
    Write-Host "  - minio"
    Write-Host "  - mongodb"
    Write-Host ""
    Write-Host "Exemples:" -ForegroundColor Green
    Write-Host "  .\manage.ps1 init                    " -NoNewline -ForegroundColor Gray
    Write-Host "# Setup complet"
    Write-Host "  .\manage.ps1 start                   " -NoNewline -ForegroundColor Gray
    Write-Host "# Démarre tout"
    Write-Host "  .\manage.ps1 start recommendation    " -NoNewline -ForegroundColor Gray
    Write-Host "# Service spécifique"
    Write-Host "  .\manage.ps1 rebuild api-gateway     " -NoNewline -ForegroundColor Gray
    Write-Host "# Rebuild + redémarre"
    Write-Host "  .\manage.ps1 logs job-sourcing -Follow" -NoNewline -ForegroundColor Gray
    Write-Host " # Logs temps réel"
    Write-Host "  .\manage.ps1 cors                    " -NoNewline -ForegroundColor Gray
    Write-Host "# Régénère CORS (*  dev)"
    Write-Host "  .\manage.ps1 scale search-engine 3   " -NoNewline -ForegroundColor Gray
    Write-Host "# 3 instances"
    Write-Host "  .\manage.ps1 auto api                " -NoNewline -ForegroundColor Gray
    Write-Host "# Start minimal pour API"
    Write-Host "  .\manage.ps1 auto sourcing-full trim " -NoNewline -ForegroundColor Gray
    Write-Host "# Start pipeline sourcing + stop services inutiles"
    Write-Host "  .\manage.ps1 auto status             " -NoNewline -ForegroundColor Gray
    Write-Host "# Voir modes + services actifs"
    Write-Host ""
}

# Vérification .env
function Test-EnvFile {
    $envPath = Join-Path $ProjectRoot ".env"
    
    if (-not (Test-Path $envPath)) {
        Write-Host "⚠️  Fichier .env manquant" -ForegroundColor Yellow
        Write-Host ""
        $createEnv = Read-Host "Créer automatiquement? [Y/n]"
        
        if ($createEnv -ne "n" -and $createEnv -ne "N") {
            New-EnvFile -EnvPath $envPath
        } else {
            Write-Host "❌ .env requis pour continuer" -ForegroundColor Red
            exit 1
        }
    }
}

# Init projet complet
function Initialize-Project {
    Show-Banner
    Write-Host "🔧 Initialisation TalentFlow" -ForegroundColor Blue
    Write-Host ""
    
    $envPath = Join-Path $ProjectRoot ".env"
    
    # 1. Créer .env si manquant
    if (-not (Test-Path $envPath)) {
        New-EnvFile -EnvPath $envPath
    } else {
        Write-Host "ℹ️  .env déjà existant (skip)" -ForegroundColor Gray
    }
    
    # 2. Créer réseau Docker
    New-DockerNetwork
    
    # 3. Créer dossiers requis
    Write-Host ""
    Write-Host "📁 Création structure dossiers..." -ForegroundColor Cyan
    New-Item -ItemType Directory -Path "logs" -Force | Out-Null
    New-Item -ItemType Directory -Path "backups" -Force | Out-Null
    
    # 4. Build images
    Write-Host ""
    Write-Host "🏗️  Build images Docker..." -ForegroundColor Cyan
    docker-compose build
    
    # 5. Démarrer services
    Write-Host ""
    Write-Host "🚀 Démarrage services..." -ForegroundColor Cyan
    docker-compose up -d
    
    # 6. Attendre services
    Write-Host ""
    Write-Host "⏳ Attente démarrage services (30s)..." -ForegroundColor Yellow
    Start-Sleep -Seconds 30
    
    # 7. Health check
    Write-Host ""
    Test-ServicesHealth
    
    Write-Host ""
    Write-Host "✅ Initialisation terminée!" -ForegroundColor Green
    Write-Host ""
    Write-Host "🌍 Accès services:" -ForegroundColor Cyan
    Write-Host "  - API Gateway: http://localhost:3000"
    Write-Host "  - Grafana: http://localhost:3001 (admin / voir .env)"
    Write-Host "  - Airflow: http://localhost:8080"
    Write-Host "  - MinIO Console: http://localhost:9001"
    Write-Host ""
}

# Main
Set-Location $ProjectRoot

switch ($Command) {
    "init" {
        Initialize-Project
    }
    "start" {
        Test-EnvFile
        Start-TalentFlowService -ServiceName $ServiceName
    }
    "stop" {
        Stop-TalentFlowService -ServiceName $ServiceName
    }
    "restart" {
        Test-EnvFile
        Restart-TalentFlowService -ServiceName $ServiceName
    }
    "rebuild" {
        Test-EnvFile
        Rebuild-TalentFlowService -ServiceName $ServiceName
    }
    "logs" {
        if ($Follow) {
            Get-ServiceLogs -ServiceName $ServiceName -Follow
        } else {
            Get-ServiceLogs -ServiceName $ServiceName
        }
    }
    "status" {
        Get-ServicesStatus
    }
    "health" {
        Test-ServicesHealth
    }
    "env" {
        $envPath = Join-Path $ProjectRoot ".env"
        New-EnvFile -EnvPath $envPath
    }
    "cors" {
        $envPath = Join-Path $ProjectRoot ".env"
        if (-not (Test-Path $envPath)) {
            Write-Host ".env manquant" -ForegroundColor Red
            exit 1
        }
        Update-CorsOnly -EnvPath $envPath
    }
    "backup" {
        Backup-DockerVolumes
    }
    "restore" {
        Restore-DockerVolumes -BackupDir $ServiceName
    }
    "prune" {
        Invoke-DockerPrune
    }
    "scale" {
        Set-ServiceScale -ServiceName $ServiceName -Replicas ([int]$Extra)
    }
    "auto" {
        $autoOptions = if ($Extra -is [System.Array]) {
            (($Extra | ForEach-Object { "$_" }) -join ",")
        } else {
            [string]$Extra
        }
        Invoke-AutoOrchestration -Mode $ServiceName -Options $autoOptions
    }
    default {
        Show-Help
    }
}


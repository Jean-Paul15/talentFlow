# Quick Start PowerShell - Démarrage rapide en 3 étapes
# Usage: .\scripts\powershell\quick-start.ps1

$RED = "Red"
$GREEN = "Green"
$YELLOW = "Yellow"
$BLUE = "Cyan"

Write-Host ""
Write-Host "╔════════════════════════════════════════════╗" -ForegroundColor $BLUE
Write-Host "║  TALENTFLOW QUICK START                    ║" -ForegroundColor $BLUE
Write-Host "║  Démarrage rapide en 3 étapes              ║" -ForegroundColor $BLUE
Write-Host "╚════════════════════════════════════════════╝" -ForegroundColor $BLUE
Write-Host ""

# ÉTAPE 1: Vérifications
Write-Host "ÉTAPE 1: Vérifications préalables..." -ForegroundColor $BLUE

try {
    docker --version | Out-Null
    Write-Host "OK - Docker détecté" -ForegroundColor $GREEN
} catch {
    Write-Host "Erreur: Docker n'est pas installé" -ForegroundColor $RED
    Write-Host "Installer depuis: https://docs.docker.com/engine/install/"
    exit 1
}

try {
    docker-compose --version | Out-Null
    Write-Host "OK - Docker Compose détecté" -ForegroundColor $GREEN
} catch {
    Write-Host "Erreur: Docker Compose n'est pas installé" -ForegroundColor $RED
    exit 1
}

# ÉTAPE 2: Configuration .env
Write-Host "`nÉTAPE 2: Configuration (.env)..." -ForegroundColor $BLUE

if (Test-Path ".env") {
    Write-Host "Le fichier .env existe déjà" -ForegroundColor $YELLOW
    $response = Read-Host "Voulez-vous le régénérer? (o/n)"
    if ($response -eq "o") {
        Remove-Item ".env" -Force
    } else {
        Write-Host "Utilisation du .env existant" -ForegroundColor $GREEN
    }
}

if (-not (Test-Path ".env")) {
    Write-Host "Génération du fichier .env..." -ForegroundColor $YELLOW
    
    if (Test-Path "scripts/powershell/env-generator-clean.ps1") {
        & "scripts/powershell/env-generator-clean.ps1"
        Write-Host "OK - Fichier .env créé" -ForegroundColor $GREEN
    } else {
        Write-Host "Erreur: Script env-generator-clean.ps1 non trouvé" -ForegroundColor $RED
        exit 1
    }
}

# ÉTAPE 3: Démarrage services
Write-Host "`nÉTAPE 3: Démarrage des services..." -ForegroundColor $BLUE

if (-not (Test-Path "docker-compose.yml")) {
    Write-Host "Erreur: docker-compose.yml non trouvé" -ForegroundColor $RED
    exit 1
}

Write-Host "Démarrage des containers..." -ForegroundColor $YELLOW
docker-compose up -d

# Attendre
Write-Host "Attendre initialisation des services (5s)..."
Start-Sleep -Seconds 5

# Vérifier
$runningServices = docker-compose ps -q
if ($runningServices) {
    Write-Host "OK - Services démarrés" -ForegroundColor $GREEN
} else {
    Write-Host "Erreur: Certains services n'ont pas démarré" -ForegroundColor $RED
    Write-Host "Consulter: docker-compose logs"
    exit 1
}

# RÉSUMÉ FINAL
Write-Host "`n════════════════════════════════════════════" -ForegroundColor $BLUE
Write-Host "DÉMARRAGE COMPLÉTÉ!" -ForegroundColor $GREEN
Write-Host "════════════════════════════════════════════`n" -ForegroundColor $BLUE

Write-Host "Services disponibles:" -ForegroundColor $BLUE
Write-Host "  API Gateway           http://localhost:3000" -ForegroundColor $GREEN
Write-Host "  Recommendation        http://localhost:8001" -ForegroundColor $GREEN
Write-Host "  Job Sourcing          http://localhost:8000" -ForegroundColor $GREEN
Write-Host "  PostgreSQL            localhost:5432" -ForegroundColor $GREEN
Write-Host "  Redis                 localhost:6379" -ForegroundColor $GREEN

Write-Host "`nCommandes utiles:" -ForegroundColor $BLUE
Write-Host "  Voir logs:            docker-compose logs -f" -ForegroundColor $YELLOW
Write-Host "  Arrêter services:     docker-compose down" -ForegroundColor $YELLOW
Write-Host "  Deploy checklist:     .\scripts\powershell\deploy-checklist.ps1" -ForegroundColor $YELLOW

Write-Host "`nPrêt pour développement/test!`n" -ForegroundColor $GREEN

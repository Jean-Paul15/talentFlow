# Script de demarrage TalentFlow
# Usage :
#   .\START.ps1              -> Lance infra + sourcing (defaut)
#   .\START.ps1 -All         -> Lance tous les services
#   .\START.ps1 -Logs        -> Affiche les logs apres le demarrage
#   .\START.ps1 -Rebuild     -> Force le rebuild des images
#   .\START.ps1 -Stop        -> Arrete tout

param(
    [switch]$All,
    [switch]$Logs,
    [switch]$Rebuild,
    [switch]$Stop
)

$ErrorActionPreference = "Continue"
Set-Location $PSScriptRoot

# -- Arret si demande --
if ($Stop) {
    Write-Host "`n[ARRET] Arret de tous les services..." -ForegroundColor Yellow
    docker compose --profile sourcing --profile monitoring --profile api --profile orchestration --profile ml down
    Write-Host "[OK] Services arretes." -ForegroundColor Green
    return
}

Write-Host "`n========================================" -ForegroundColor Cyan
Write-Host "   LANCEMENT TALENTFLOW" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan

# -- Etape 1 : Nettoyage --
Write-Host "`n[1/5] Nettoyage des conteneurs arretes..." -ForegroundColor Yellow
docker compose down --remove-orphans 2>$null

# -- Etape 2 : Choix des profils --
$profiles = @("--profile", "sourcing")
$label = "sourcing (job-sourcing + data-cleaning + streamlit)"

if ($All) {
    $profiles = @("--profile", "sourcing", "--profile", "monitoring", "--profile", "api", "--profile", "orchestration", "--profile", "ml")
    $label = "tous les services"
}

Write-Host "[2/5] Profil : $label" -ForegroundColor Yellow

# -- Etape 3 : Build si demande --
if ($Rebuild) {
    Write-Host "[3/5] Rebuild des images (peut prendre quelques minutes)..." -ForegroundColor Yellow
    docker compose @profiles build --no-cache
} else {
    Write-Host "[3/5] Build des images (cache actif)..." -ForegroundColor Yellow
    docker compose @profiles build
}

# -- Etape 4 : Demarrage --
Write-Host "[4/5] Demarrage des services..." -ForegroundColor Yellow
docker compose @profiles up -d

# -- Etape 5 : Verification --
Write-Host "`n[5/5] Verification du demarrage..." -ForegroundColor Yellow

$maxWait = 90
$elapsed = 0

while ($elapsed -lt $maxWait) {
    Start-Sleep -Seconds 5
    $elapsed += 5
    $status = docker compose @profiles ps --format "table {{.Name}}\t{{.Status}}" 2>$null
    $running = ($status | Select-String "Up" | Measure-Object).Count
    $total = ($status | Select-String -Pattern "backend-" | Measure-Object).Count
    Write-Host "  [$elapsed s] $running/$total services demarres..." -ForegroundColor Gray
    if ($running -ge $total -and $total -gt 0) { break }
}

# -- Resultat --
Write-Host "`n========================================" -ForegroundColor Cyan
Write-Host "   ETAT DES SERVICES" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
docker compose @profiles ps --format "table {{.Name}}\t{{.Status}}\t{{.Ports}}"

Write-Host "`n========================================" -ForegroundColor Green
Write-Host "   INTERFACES DISPONIBLES" -ForegroundColor Green
Write-Host "========================================" -ForegroundColor Green
Write-Host "  Dashboard :  http://localhost:8501" -ForegroundColor Cyan
Write-Host "  MinIO     :  http://localhost:9001" -ForegroundColor Gray

if ($All) {
    Write-Host "  Airflow   :  http://localhost:8080  (admin/admin)" -ForegroundColor Gray
    Write-Host "  Grafana   :  http://localhost:3001  (admin/password)" -ForegroundColor Gray
    Write-Host "  API       :  http://localhost:3000" -ForegroundColor Gray
}

Write-Host "`nCommandes utiles :" -ForegroundColor White
Write-Host "  .\START.ps1 -Logs       Voir les logs en direct" -ForegroundColor Yellow
Write-Host "  .\START.ps1 -Stop       Arreter tout" -ForegroundColor Yellow
Write-Host "  .\START.ps1 -Rebuild    Reconstruire les images" -ForegroundColor Yellow

# -- Logs si demande --
if ($Logs) {
    Write-Host "`n[LOGS] Affichage des logs en direct (Ctrl+C pour quitter)..." -ForegroundColor Yellow
    docker compose @profiles logs -f --tail 50
}

Write-Host ""

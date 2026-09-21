# Deploy Checklist PowerShell - Vérifications avant production TalentFlow
# Usage: .\scripts\powershell\deploy-checklist.ps1

$RED = "Red"
$GREEN = "Green"
$YELLOW = "Yellow"
$BLUE = "Cyan"

$checksPassed = 0
$checksFailed = 0
$checksWarning = 0

Write-Host "=== TALENTFLOW DEPLOYMENT CHECKLIST ===" -ForegroundColor $BLUE
Write-Host ""

function Check-Pass {
    param([string]$message)
    Write-Host "[PASS] $message" -ForegroundColor $GREEN
    $script:checksPassed++
}

function Check-Fail {
    param([string]$message)
    Write-Host "[FAIL] $message" -ForegroundColor $RED
    $script:checksFailed++
}

function Check-Warn {
    param([string]$message)
    Write-Host "[WARN] $message" -ForegroundColor $YELLOW
    $script:checksWarning++
}

# 1. FICHIERS
Write-Host "1. FICHIERS CONFIGURATION" -ForegroundColor $BLUE

if (Test-Path ".env") {
    Check-Pass "Fichier .env existe"
} else {
    Check-Fail "Fichier .env MANQUANT"
}

if (Test-Path "docker-compose.yml") {
    Check-Pass "docker-compose.yml existe"
} else {
    Check-Fail "docker-compose.yml MANQUANT"
}

if (Test-Path "recommendation") {
    Check-Pass "Dossier recommendation existe"
} else {
    Check-Fail "Dossier recommendation MANQUANT"
}

# 2. VARIABLES ENVIRONNEMENT
Write-Host "`n2. VARIABLES ENVIRONNEMENT" -ForegroundColor $BLUE

if (Test-Path ".env") {
    $envContent = Get-Content ".env"
    
    if ($envContent | Select-String "LLM_PROVIDER=" -Quiet) {
        $llm = ($envContent | Select-String "LLM_PROVIDER=").ToString().Split("=")[1]
        Check-Pass "LLM_PROVIDER défini: $llm"
    } else {
        Check-Fail "LLM_PROVIDER non défini"
    }
    
    if ($envContent | Select-String "POSTGRES_PASSWORD=" -Quiet) {
        Check-Pass "POSTGRES_PASSWORD défini"
    } else {
        Check-Fail "POSTGRES_PASSWORD non défini"
    }
    
    if ($envContent | Select-String "JWT_SECRET=" -Quiet) {
        Check-Pass "JWT_SECRET défini"
    } else {
        Check-Fail "JWT_SECRET non défini"
    }
    
    if ($envContent | Select-String "REDIS_HOST=" -Quiet) {
        Check-Pass "REDIS_HOST défini"
    } else {
        Check-Fail "REDIS_HOST non défini"
    }
} else {
    Check-Warn "Impossible de vérifier .env"
}

# 3. SERVICES DOCKER
Write-Host "`n3. SERVICES DOCKER" -ForegroundColor $BLUE

try {
    docker --version | Out-Null
    Check-Pass "Docker installé"
} catch {
    Check-Fail "Docker NOT installed"
}

try {
    docker-compose --version | Out-Null
    Check-Pass "Docker Compose installé"
} catch {
    Check-Fail "Docker Compose NOT installed"
}

# 4. DÉPENDANCES PYTHON
Write-Host "`n4. DÉPENDANCES PYTHON" -ForegroundColor $BLUE

try {
    $pythonVersion = python --version 2>&1
    Check-Pass "Python installé: $pythonVersion"
    
    try {
        python -c "import fastapi" 2> $null
        Check-Pass "FastAPI disponible"
    } catch {
        Check-Warn "FastAPI non installé"
    }
    
    try {
        python -c "import langchain" 2> $null
        Check-Pass "LangChain disponible"
    } catch {
        Check-Warn "LangChain non installé"
    }
} catch {
    Check-Fail "Python NOT installed"
}

# 5. PORTS DISPONIBLES
Write-Host "`n5. PORTS DISPONIBLES" -ForegroundColor $BLUE

function Check-Port {
    param([int]$port)
    try {
        $connection = New-Object System.Net.Sockets.TcpClient
        $connection.Connect("localhost", $port)
        $connection.Close()
        Check-Warn "Port $port est OCCUPÉ"
    } catch {
        Check-Pass "Port $port est libre"
    }
}

Check-Port 3000   # API Gateway
Check-Port 8000   # Job Sourcing
Check-Port 8001   # Recommendation
Check-Port 5432   # PostgreSQL
Check-Port 6379   # Redis

# 6. SÉCURITÉ
Write-Host "`n6. SÉCURITÉ" -ForegroundColor $BLUE

if (Test-Path ".env") {
    $envContent = Get-Content ".env" -Raw
    
    if ($envContent -match "ALLOWED_ORIGINS=\*") {
        Check-Warn "ALLOWED_ORIGINS='*' - OK pour DEV, restreindre en PROD"
    } else {
        Check-Pass "ALLOWED_ORIGINS restreint"
    }
    
    if ($envContent -match "JWT_SECRET=|SECRET_KEY=") {
        Check-Pass "SECRET défini"
    } else {
        Check-Warn "Pas de SECRET"
    }
}

# RÉSUMÉ
Write-Host "`n========== RÉSUMÉ ==========" -ForegroundColor $BLUE
Write-Host "Passed:  $checksPassed" -ForegroundColor $GREEN
Write-Host "Warning: $checksWarning" -ForegroundColor $YELLOW
Write-Host "Failed:  $checksFailed" -ForegroundColor $RED

if ($checksFailed -eq 0) {
    Write-Host "`nPrêt pour déploiement!" -ForegroundColor $GREEN
} else {
    Write-Host "`nCorriger les erreurs avant déploiement" -ForegroundColor $RED
}

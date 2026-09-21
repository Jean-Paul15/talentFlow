# Troubleshoot PowerShell - Diagnostic LLM / runtime TalentFlow

$RED = "Red"
$GREEN = "Green"
$YELLOW = "Yellow"
$BLUE = "Cyan"
$issuesFound = 0

function Log-Issue {
    param([string]$Message)
    Write-Host "[ISSUE] $Message" -ForegroundColor $RED
    $script:issuesFound++
}

function Log-Info {
    param([string]$Message)
    Write-Host "[INFO] $Message" -ForegroundColor $BLUE
}

function Log-Debug {
    param([string]$Message)
    Write-Host "[DEBUG] $Message" -ForegroundColor $YELLOW
}

Write-Host "=== TALENTFLOW TROUBLESHOOTING TOOL ===" -ForegroundColor $BLUE

if (-not (Test-Path ".env")) {
    Log-Issue "Fichier .env manquant"
} else {
    $envContent = Get-Content ".env"

    if ($envContent | Select-String "^LLM_PROVIDER=gemini" -Quiet) {
        Log-Info "Recommendation provider: gemini"
    } else {
        Log-Issue "LLM_PROVIDER doit valoir gemini"
    }

    if ($envContent | Select-String "^GEMINI_API_KEY=." -Quiet) {
        Log-Info "Gemini API key principale configuree"
    } else {
        Log-Issue "Gemini API key principale manquante"
    }

    if ($envContent | Select-String "^DATA_CLEANING_LLM_PROVIDER=mistral" -Quiet) {
        Log-Info "Data-cleaning provider: mistral"
    } else {
        Log-Issue "DATA_CLEANING_LLM_PROVIDER doit valoir mistral"
    }

    if ($envContent | Select-String "^DATA_CLEANING_LLM_ENABLED=true" -Quiet) {
        if ($envContent | Select-String "^MISTRAL_API_KEY=." -Quiet) {
            Log-Info "Mistral API key configuree"
        } else {
            Log-Issue "Mistral API key manquante alors que DATA_CLEANING_LLM_ENABLED=true"
        }
    } else {
        Log-Debug "Data-cleaning LLM desactive (tolere)"
    }

}

try {
    docker compose -f backend/docker-compose.yml config | Out-Null
    Log-Info "docker compose config standard OK"
} catch {
    Log-Issue "docker compose config standard en echec"
}

if ($issuesFound -eq 0) {
    Write-Host "Aucun probleme detecte" -ForegroundColor $GREEN
} else {
    Write-Host "$issuesFound probleme(s) detecte(s)" -ForegroundColor $RED
}

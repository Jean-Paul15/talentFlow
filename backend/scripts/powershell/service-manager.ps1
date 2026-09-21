# Service Manager PowerShell - Gestion services Docker

function Start-TalentFlowService {
    param([string]$ServiceName)
    
    if ([string]::IsNullOrWhiteSpace($ServiceName)) {
        Write-Host "Demarrage de TOUS les services..." -ForegroundColor Cyan
        docker-compose up -d
    } else {
        Write-Host "Demarrage de $ServiceName..." -ForegroundColor Cyan
        docker-compose up -d $ServiceName
    }
    
    Write-Host "Service(s) demarres" -ForegroundColor Green
}

function Stop-TalentFlowService {
    param([string]$ServiceName)
    
    if ([string]::IsNullOrWhiteSpace($ServiceName)) {
        Write-Host "Arret de TOUS les services..." -ForegroundColor Yellow
        docker-compose down
    } else {
        Write-Host "Arret de $ServiceName..." -ForegroundColor Yellow
        docker-compose stop $ServiceName
    }
    
    Write-Host "Service(s) arretes" -ForegroundColor Green
}

function Restart-TalentFlowService {
    param(
        [string]$ServiceName
    )
    
    Write-Host "🔄 Redémarrage..." -ForegroundColor Cyan
    Stop-TalentFlowService $ServiceName
    Start-Sleep -Seconds 2
    Start-TalentFlowService $ServiceName
}

function Rebuild-TalentFlowService {
    param([string]$ServiceName)
    
    if ([string]::IsNullOrWhiteSpace($ServiceName)) {
        Write-Host "Rebuild de TOUS les services..." -ForegroundColor Cyan
        docker-compose build
        docker-compose up -d
    } else {
        Write-Host "Rebuild de $ServiceName..." -ForegroundColor Cyan
        docker-compose build $ServiceName
        docker-compose up -d $ServiceName
    }
    
    Write-Host "Service(s) rebuildes et demarres" -ForegroundColor Green
}

function Get-ServiceLogs {
    param([string]$ServiceName, [switch]$Follow)
    
    if ($Follow) {
        if ([string]::IsNullOrWhiteSpace($ServiceName)) {
            docker-compose logs -f
        } else {
            docker-compose logs -f $ServiceName
        }
    } else {
        if ([string]::IsNullOrWhiteSpace($ServiceName)) {
            docker-compose logs --tail=100
        } else {
            docker-compose logs --tail=100 $ServiceName
        }
    }
}

function Get-ServicesStatus {
    Write-Host "Status des services TalentFlow:" -ForegroundColor Cyan
    Write-Host ""
    docker-compose ps
}

function Test-ServicesHealth {
    Write-Host "Verification sante des services..." -ForegroundColor Cyan
    Write-Host ""
    
    $services = @(
        @{Name="api-gateway"; Port=3000},
        @{Name="job-sourcing"; Port=8000},
        @{Name="recommendation"; Port=8001},
        @{Name="data-cleaning"; Port=8002},
        @{Name="search-engine"; Port=8003}
    )
    
    foreach ($service in $services) {
        try {
            $response = Invoke-WebRequest -Uri "http://localhost:$($service.Port)/health" -TimeoutSec 5 -ErrorAction Stop
            Write-Host "OK: $($service.Name) (port $($service.Port)): HEALTHY" -ForegroundColor Green
        } catch {
            Write-Host "ERROR: $($service.Name) (port $($service.Port)): UNHEALTHY" -ForegroundColor Red
        }
    }
}

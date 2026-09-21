# Docker Operations PowerShell - Operations avancees

function Invoke-DockerPrune {
    Write-Host "Nettoyage Docker..." -ForegroundColor Cyan
    Write-Host ""
    
    $confirm = Read-Host "Supprimer containers arretes, images non utilisees, volumes? (y/N)"
    
    if ($confirm -eq "y" -or $confirm -eq "Y") {
        docker system prune -a --volumes -f
        Write-Host "Nettoyage termine" -ForegroundColor Green
    } else {
        Write-Host "Annule" -ForegroundColor Yellow
    }
}

function Backup-DockerVolumes {
    $timestamp = Get-Date -Format "yyyyMMdd_HHmmss"
    $backupDir = ".\backups\$timestamp"
    
    Write-Host "Backup des volumes Docker..." -ForegroundColor Cyan
    New-Item -ItemType Directory -Path $backupDir -Force | Out-Null
    
    $volumes = @("postgres_data", "mongodb_data", "minio_data", "grafana_data")
    
    foreach ($volume in $volumes) {
        Write-Host "  Backup $volume..." -ForegroundColor Gray
        $hostBackupPath = (Join-Path (Get-Location).Path $backupDir).Replace('\', '/')

        docker run --rm `
            -v "${volume}:/data" `
            -v "${hostBackupPath}:/backup" `
            alpine tar czf "/backup/${volume}.tar.gz" -C /data .
    }
    
    Write-Host "Backups crees dans $backupDir" -ForegroundColor Green
}

function Restore-DockerVolumes {
    param([string]$BackupDir)
    
    if ([string]::IsNullOrWhiteSpace($BackupDir)) {
        Write-Host "Erreur: Specifier le dossier de backup" -ForegroundColor Red
        return
    }
    
    Write-Host "Restauration depuis $BackupDir..." -ForegroundColor Cyan
    
    $confirm = Read-Host "Ceci ecrasera les donnees actuelles. Continuer? (y/N)"
    
    if ($confirm -ne "y" -and $confirm -ne "Y") {
        Write-Host "Annule" -ForegroundColor Yellow
        return
    }
    
    $archives = Get-ChildItem -Path $BackupDir -Filter "*.tar.gz"
    
    foreach ($archive in $archives) {
        $volume = $archive.BaseName
        Write-Host "  Restauration $volume..." -ForegroundColor Gray
        $hostBackupPath = (Join-Path (Get-Location).Path $BackupDir).Replace('\', '/')

        docker run --rm `
            -v "${volume}:/data" `
            -v "${hostBackupPath}:/backup" `
            alpine sh -c "rm -rf /data/* && tar xzf /backup/$($archive.Name) -C /data"
    }
    
    Write-Host "Restauration terminee" -ForegroundColor Green
}

function New-DockerNetwork {
    try {
        docker network inspect talentflow_network | Out-Null
        Write-Host "Reseau talentflow_network deja existant" -ForegroundColor Gray
    } catch {
        Write-Host "Creation reseau talentflow_network..." -ForegroundColor Cyan
        docker network create talentflow_network
        Write-Host "Reseau cree" -ForegroundColor Green
    }
}

function Set-ServiceScale {
    param([string]$ServiceName, [int]$Replicas)
    
    if ([string]::IsNullOrWhiteSpace($ServiceName) -or $Replicas -eq 0) {
        Write-Host "Erreur: Specifier le service et le nombre de replicas" -ForegroundColor Red
        return
    }
    
    Write-Host "Scaling $ServiceName a $Replicas instances..." -ForegroundColor Cyan
    docker-compose up -d --scale "${ServiceName}=$Replicas"
    Write-Host "Service scale" -ForegroundColor Green
}

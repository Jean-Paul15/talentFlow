# Smart orchestrator for Docker services (on-demand start/stop)

$script:AutoModeEntry = @{
    "sourcing-lite" = @("job-sourcing", "spark-streaming", "lake-api")
    "sourcing-full" = @("job-sourcing", "spark-streaming", "data-cleaning", "lake-api")
    "pipeline"      = @("job-sourcing", "spark-streaming", "data-cleaning", "search-engine", "recommendation")
    "search"        = @("search-engine")
    "recommendation"= @("recommendation")
    "api"           = @("api-gateway")
    "dashboard"     = @("streamlit")
    "lake-only"     = @("lake-api", "streamlit")
    "orchestration" = @("airflow")
    "monitoring"    = @("prometheus", "grafana")
    "all"           = @("api-gateway", "streamlit", "airflow", "prometheus", "grafana", "job-sourcing", "data-cleaning", "spark-streaming")
}

$script:ServiceDeps = @{
    "api-gateway"    = @("postgres", "redis", "search-engine", "recommendation")
    "recommendation" = @("search-engine", "redis")
    "search-engine"  = @("mongodb", "qdrant")
    "streamlit"      = @("lake-api", "minio")
    "lake-api"       = @("minio")
    "job-sourcing"   = @("minio", "redis", "kafka")
    "spark-streaming"= @("kafka", "minio")
    "data-cleaning"  = @("minio", "mongodb")
    "airflow"        = @("postgres", "kafka")
    "kafka"          = @("zookeeper")
    "grafana"        = @("prometheus")
}

$script:ModeHealthChecks = @{
    "sourcing-lite" = @(
        @{ name = "job-sourcing"; url = "http://localhost:8000/health" },
        @{ name = "lake-api"; url = "http://localhost:8004/health" }
    )
    "sourcing-full" = @(
        @{ name = "job-sourcing"; url = "http://localhost:8000/health" },
        @{ name = "data-cleaning"; url = "http://localhost:8002/health" },
        @{ name = "lake-api"; url = "http://localhost:8004/health" }
    )
    "pipeline" = @(
        @{ name = "job-sourcing"; url = "http://localhost:8000/health" },
        @{ name = "data-cleaning"; url = "http://localhost:8002/health" },
        @{ name = "search-engine"; url = "http://localhost:8003/health" },
        @{ name = "recommendation"; url = "http://localhost:8001/health" }
    )
    "search" = @(
        @{ name = "search-engine"; url = "http://localhost:8003/health" }
    )
    "recommendation" = @(
        @{ name = "recommendation"; url = "http://localhost:8001/health" }
    )
    "api" = @(
        @{ name = "api-gateway"; url = "http://localhost:3000/health" }
    )
    "dashboard" = @(
        @{ name = "streamlit"; url = "http://localhost:8501/_stcore/health" }
    )
    "lake-only" = @(
        @{ name = "streamlit"; url = "http://localhost:8501/_stcore/health" },
        @{ name = "lake-api"; url = "http://localhost:8004/health" }
    )
    "orchestration" = @(
        @{ name = "airflow"; url = "http://localhost:8080/health" }
    )
    "monitoring" = @(
        @{ name = "prometheus"; url = "http://localhost:9090/-/healthy" },
        @{ name = "grafana"; url = "http://localhost:3001/api/health" }
    )
}

function Get-AutoModes {
    return @($script:AutoModeEntry.Keys | Sort-Object)
}

function Get-RunningServices {
    $lines = docker-compose ps --services --filter "status=running" 2>$null
    if (-not $lines) {
        return @()
    }
    return @($lines | ForEach-Object { "$_".Trim() } | Where-Object { $_ })
}

function Expand-ServiceSet {
    param([string[]]$Services)

    $seen = New-Object "System.Collections.Generic.HashSet[string]" ([System.StringComparer]::OrdinalIgnoreCase)
    $queue = New-Object "System.Collections.Generic.Queue[string]"
    foreach ($svc in $Services) {
        if (-not [string]::IsNullOrWhiteSpace($svc)) {
            $queue.Enqueue($svc.Trim())
        }
    }

    while ($queue.Count -gt 0) {
        $svc = $queue.Dequeue()
        if ($seen.Add($svc) -and $script:ServiceDeps.ContainsKey($svc)) {
            foreach ($dep in $script:ServiceDeps[$svc]) {
                $queue.Enqueue($dep)
            }
        }
    }

    return @($seen)
}

function Resolve-ModeServices {
    param([string[]]$Modes)

    $entries = @()
    foreach ($mode in $Modes) {
        if (-not $script:AutoModeEntry.ContainsKey($mode)) {
            throw "Mode inconnu: $mode"
        }
        $entries += $script:AutoModeEntry[$mode]
    }
    return Expand-ServiceSet -Services $entries
}

function Test-EndpointReady {
    param(
        [string]$Url,
        [int]$TimeoutSeconds = 120
    )
    $deadline = (Get-Date).AddSeconds($TimeoutSeconds)
    while ((Get-Date) -lt $deadline) {
        try {
            Invoke-WebRequest -Uri $Url -Method Get -TimeoutSec 4 -ErrorAction Stop | Out-Null
            return $true
        } catch {
            Start-Sleep -Seconds 2
        }
    }
    return $false
}

function Wait-ModeHealth {
    param(
        [string[]]$Modes,
        [int]$TimeoutPerCheck = 120
    )

    $checks = @()
    foreach ($mode in $Modes) {
        if ($script:ModeHealthChecks.ContainsKey($mode)) {
            $checks += $script:ModeHealthChecks[$mode]
        }
    }

    if (-not $checks) {
        return
    }

    $seen = New-Object "System.Collections.Generic.HashSet[string]" ([System.StringComparer]::OrdinalIgnoreCase)
    foreach ($check in $checks) {
        $url = [string]$check.url
        if (-not $seen.Add($url)) {
            continue
        }
        $name = [string]$check.name
        if (Test-EndpointReady -Url $url -TimeoutSeconds $TimeoutPerCheck) {
            Write-Host "OK: $name ($url)" -ForegroundColor Green
        } else {
            Write-Host "WARN: $name non pret ($url)" -ForegroundColor Yellow
        }
    }
}

function Show-AutoStatus {
    Write-Host "Modes disponibles: $((Get-AutoModes) -join ', ')" -ForegroundColor Cyan
    $running = Get-RunningServices
    if (-not $running -or $running.Count -eq 0) {
        Write-Host "Aucun service en cours." -ForegroundColor Yellow
        return
    }
    Write-Host "Services en cours: $($running -join ', ')" -ForegroundColor Green
}

function Invoke-AutoOrchestration {
    param(
        [string]$Mode,
        [string]$Options = ""
    )

    $modeValue = [string]$Mode
    if ($null -eq $modeValue) {
        $modeValue = ""
    }
    $modeValue = $modeValue.Trim().ToLowerInvariant()
    $optTokens = @()
    if (-not [string]::IsNullOrWhiteSpace($Options)) {
        $optTokens = @($Options.ToLowerInvariant() -split "[,; ]+" | Where-Object { $_ })
    }

    if ($modeValue -in @("status", "list", "modes")) {
        Show-AutoStatus
        return
    }
    if ([string]::IsNullOrWhiteSpace($modeValue)) {
        throw "Mode requis. Ex: auto api"
    }

    $modes = @($modeValue.Split(@("+", ","), [System.StringSplitOptions]::RemoveEmptyEntries) | ForEach-Object { $_.Trim().ToLowerInvariant() })
    $target = Resolve-ModeServices -Modes $modes

    $trim = $optTokens -contains "trim"
    $down = $optTokens -contains "down"
    $noWait = $optTokens -contains "nowait"

    $running = Get-RunningServices
    if ($down) {
        $toStop = @($running | Where-Object { $target -contains $_ })
        if ($toStop.Count -gt 0) {
            Write-Host "Arret mode [$($modes -join '+')]: $($toStop -join ', ')" -ForegroundColor Yellow
            docker-compose stop $toStop
        } else {
            Write-Host "Rien a arreter pour ce mode." -ForegroundColor Gray
        }
        return
    }

    $missing = @($target | Where-Object { $running -notcontains $_ })
    if ($missing.Count -gt 0) {
        Write-Host "Demarrage on-demand mode [$($modes -join '+')]: $($missing -join ', ')" -ForegroundColor Cyan
        docker-compose up -d $missing
    } else {
        Write-Host "Mode [$($modes -join '+')] deja pret (aucun service manquant)." -ForegroundColor Green
    }

    if ($trim) {
        $runningAfter = Get-RunningServices
        $toStop = @($runningAfter | Where-Object { $target -notcontains $_ })
        if ($toStop.Count -gt 0) {
            Write-Host "Trim services inutiles: $($toStop -join ', ')" -ForegroundColor Yellow
            docker-compose stop $toStop
        }
    }

    if (-not $noWait) {
        Wait-ModeHealth -Modes $modes
    }
}

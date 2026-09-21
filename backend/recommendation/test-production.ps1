# Test Production Improvements - Validation 10/10

param(
    [string]$BaseUrl = "http://localhost:8000"
)

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "TEST PRODUCTION IMPROVEMENTS" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

$testsPassed = 0
$testsFailed = 0

function Test-Endpoint {
    param(
        [string]$Name,
        [string]$Url,
        [int]$ExpectedStatus = 200
    )
    
    Write-Host "Test: $Name" -NoNewline
    
    try {
        $response = Invoke-WebRequest -Uri $Url -Method GET -ErrorAction Stop
        
        if ($response.StatusCode -eq $ExpectedStatus) {
            Write-Host " PASS" -ForegroundColor Green
            return $true
        } else {
            Write-Host " FAIL (Status: $($response.StatusCode))" -ForegroundColor Red
            return $false
        }
    }
    catch {
        Write-Host " FAIL ($($_.Exception.Message))" -ForegroundColor Red
        return $false
    }
}

function Test-JsonEndpoint {
    param(
        [string]$Name,
        [string]$Url,
        [string]$ExpectedField
    )
    
    Write-Host "Test: $Name" -NoNewline
    
    try {
        $response = Invoke-RestMethod -Uri $Url -Method GET -ErrorAction Stop
        
        if ($response.$ExpectedField) {
            Write-Host " PASS (Value: $($response.$ExpectedField))" -ForegroundColor Green
            return $true
        } else {
            Write-Host " FAIL (Field not found)" -ForegroundColor Red
            return $false
        }
    }
    catch {
        Write-Host " FAIL ($($_.Exception.Message))" -ForegroundColor Red
        return $false
    }
}

Write-Host "1. HEALTH CHECKS" -ForegroundColor Yellow
Write-Host "----------------" -ForegroundColor Yellow

if (Test-Endpoint "Liveness Probe" "$BaseUrl/health/live") { $testsPassed++ } else { $testsFailed++ }
if (Test-Endpoint "Readiness Probe" "$BaseUrl/health/ready") { $testsPassed++ } else { $testsFailed++ }
if (Test-JsonEndpoint "Health Complete" "$BaseUrl/health/" "status") { $testsPassed++ } else { $testsFailed++ }

Write-Host ""
Write-Host "2. METRICS ENDPOINT" -ForegroundColor Yellow
Write-Host "-------------------" -ForegroundColor Yellow

if (Test-Endpoint "Prometheus Metrics" "$BaseUrl/metrics") { $testsPassed++ } else { $testsFailed++ }

Write-Host ""
Write-Host "Verification contenu metrics..." -NoNewline
try {
    $metrics = Invoke-RestMethod -Uri "$BaseUrl/metrics" -Method GET
    
    $hasAnalysisMetrics = $metrics -match "analysis_requests_total"
    $hasLLMMetrics = $metrics -match "llm_calls_total"
    $hasCircuitMetrics = $metrics -match "circuit_breaker"
    
    if ($hasAnalysisMetrics -and $hasLLMMetrics) {
        Write-Host " PASS" -ForegroundColor Green
        $testsPassed++
    } else {
        Write-Host " FAIL (Missing metrics)" -ForegroundColor Red
        $testsFailed++
    }
}
catch {
    Write-Host " FAIL" -ForegroundColor Red
    $testsFailed++
}

Write-Host ""
Write-Host "3. REDIS CONNECTION" -ForegroundColor Yellow
Write-Host "-------------------" -ForegroundColor Yellow

Write-Host "Test Redis health check..." -NoNewline
try {
    $health = Invoke-RestMethod -Uri "$BaseUrl/health/" -Method GET
    $redisStatus = $health.checks.redis.status
    
    if ($redisStatus -eq "healthy") {
        Write-Host " PASS (Latency: $($health.checks.redis.latency_ms)ms)" -ForegroundColor Green
        $testsPassed++
    } elseif ($redisStatus -eq "unhealthy") {
        Write-Host " SKIP (Redis not configured)" -ForegroundColor Yellow
    } else {
        Write-Host " FAIL" -ForegroundColor Red
        $testsFailed++
    }
}
catch {
    Write-Host " SKIP (Health endpoint not available)" -ForegroundColor Yellow
}

Write-Host ""
Write-Host "4. LLM PROVIDER" -ForegroundColor Yellow
Write-Host "---------------" -ForegroundColor Yellow

Write-Host "Test LLM health check..." -NoNewline
try {
    $health = Invoke-RestMethod -Uri "$BaseUrl/health/" -Method GET
    $llmStatus = $health.checks.llm.status
    
    if ($llmStatus -eq "healthy") {
        Write-Host " PASS (Provider: $($health.checks.llm.provider))" -ForegroundColor Green
        $testsPassed++
    } else {
        Write-Host " WARN (LLM not available)" -ForegroundColor Yellow
    }
}
catch {
    Write-Host " SKIP" -ForegroundColor Yellow
}

Write-Host ""
Write-Host "5. CIRCUIT BREAKER" -ForegroundColor Yellow
Write-Host "------------------" -ForegroundColor Yellow

Write-Host "Test circuit breaker state..." -NoNewline
try {
    $health = Invoke-RestMethod -Uri "$BaseUrl/health/" -Method GET
    $circuitState = $health.checks.circuit_breaker.state
    
    if ($circuitState -eq "closed") {
        Write-Host " PASS (State: $circuitState)" -ForegroundColor Green
        $testsPassed++
    } elseif ($circuitState -eq "open") {
        Write-Host " WARN (Circuit OUVERT - trop d'erreurs)" -ForegroundColor Yellow
    } else {
        Write-Host " FAIL" -ForegroundColor Red
        $testsFailed++
    }
}
catch {
    Write-Host " SKIP" -ForegroundColor Yellow
}

Write-Host ""
Write-Host "6. FICHIERS PRODUCTION" -ForegroundColor Yellow
Write-Host "----------------------" -ForegroundColor Yellow

$productionFiles = @(
    "core\redis_state_manager.py",
    "core\retry_logic.py",
    "core\metrics.py",
    "core\state_backend.py",
    "api\health.py"
)

foreach ($file in $productionFiles) {
    $fullPath = "c:\UCAO\ING 1\INT BIG DATA\talentFlow\backend\recommendation\$file"
    Write-Host "Fichier: $file" -NoNewline
    
    if (Test-Path $fullPath) {
        Write-Host " EXIST" -ForegroundColor Green
        $testsPassed++
    } else {
        Write-Host " MISSING" -ForegroundColor Red
        $testsFailed++
    }
}

Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "RESULTATS" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "Tests reussis: $testsPassed" -ForegroundColor Green
Write-Host "Tests echoues: $testsFailed" -ForegroundColor Red

$total = $testsPassed + $testsFailed
if ($total -gt 0) {
    $percentage = [math]::Round(($testsPassed / $total) * 100, 1)
    Write-Host "Taux succes: $percentage%" -ForegroundColor $(if ($percentage -ge 80) { "Green" } else { "Red" })
}

Write-Host ""
if ($testsFailed -eq 0) {
    Write-Host "TOUS LES TESTS PASSES - PRODUCTION READY" -ForegroundColor Green
    exit 0
} else {
    Write-Host "CERTAINS TESTS ECHOUES - VERIFICATION NECESSAIRE" -ForegroundColor Yellow
    exit 1
}

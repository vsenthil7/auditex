# MT-001: Health Deep Check
# TEST ID   : MT-001
# FEATURE   : GET /api/v1/health/deep -- full service connectivity check
# PHASE     : 2
# PRECONDITIONS:
#   - Docker Compose stack running (api, postgres, redis, foxmq)
#   - Seed script run: docker compose exec api python scripts/seed_test_data.py

Write-Host "=== MT-001: Health Deep Check ===" -ForegroundColor Cyan
Write-Host "Calling GET /api/v1/health/deep ..."

try {
    $wr = Invoke-WebRequest `
        -Uri "http://localhost:8000/api/v1/health/deep" `
        -Method GET `
        -Headers @{ "X-API-Key" = "auditex-test-key-phase2" } `
        -UseBasicParsing `
        -ErrorAction Stop

    $response = $wr.Content | ConvertFrom-Json
    Write-Host "`nHTTP $($wr.StatusCode)" -ForegroundColor Green
    Write-Host ($wr.Content | python -m json.tool 2>$null) 
    if ($LASTEXITCODE -ne 0) { Write-Host $wr.Content }
} catch {
    Write-Host "`n[ERROR] Request failed: $($_.Exception.Message)" -ForegroundColor Red
    if ($_.Exception.Response) {
        $reader = [System.IO.StreamReader]::new($_.Exception.Response.GetResponseStream())
        $body = $reader.ReadToEnd()
        Write-Host "Response body: $body" -ForegroundColor Red
    }
    Write-Host "`n=== MT-001 RESULT: FAIL (request error) ===" -ForegroundColor Red
    exit 1
}

# Validation
Write-Host "`n--- VALIDATION ---" -ForegroundColor Yellow
$pass = $true

if ($response.status -eq "healthy") {
    Write-Host "[PASS] status = healthy" -ForegroundColor Green
} else {
    Write-Host "[FAIL] status = '$($response.status)' (expected: healthy)" -ForegroundColor Red
    $pass = $false
}

if ($response.services.database -eq "connected") {
    Write-Host "[PASS] database = connected" -ForegroundColor Green
} else {
    Write-Host "[FAIL] database = '$($response.services.database)'" -ForegroundColor Red
    $pass = $false
}

if ($response.services.redis -eq "connected") {
    Write-Host "[PASS] redis = connected" -ForegroundColor Green
} else {
    Write-Host "[FAIL] redis = '$($response.services.redis)'" -ForegroundColor Red
    $pass = $false
}

Write-Host "[INFO] foxmq = '$($response.services.foxmq)'"
Write-Host "[INFO] vertex = '$($response.services.vertex)'"

$tables = $response.database_tables
$required = @("agents", "tasks", "audit_events", "reports")
$missing = $required | Where-Object { $tables -notcontains $_ }
if ($missing.Count -eq 0) {
    Write-Host "[PASS] database_tables: $($tables -join ', ')" -ForegroundColor Green
} else {
    Write-Host "[FAIL] missing tables: $($missing -join ', ')" -ForegroundColor Red
    $pass = $false
}

Write-Host "`n=== MT-001 RESULT: $(if ($pass) { 'PASS' } else { 'FAIL' }) ===" -ForegroundColor $(if ($pass) { 'Green' } else { 'Red' })

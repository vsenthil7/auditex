# MT-006: Vertex Consensus Complete (Stub Mode)
# Phase 5 Manual Test Script
#
# PRECONDITIONS:
#   - Real ANTHROPIC_API_KEY and OPENAI_API_KEY in .env
#   - All containers running: api, postgres, redis, celery-worker
#   - MT-005 passing (Phase 4 complete)
#   - No FoxMQ/Vertex infrastructure required (stub mode)
#
# USAGE:
#   powershell -ExecutionPolicy Bypass -File run.ps1 -cmd "powershell -ExecutionPolicy Bypass -File docs/testing/manual-test-scripts/MT-006-vertex-consensus.ps1"
#
# Or run directly:
#   powershell -ExecutionPolicy Bypass -File docs\testing\manual-test-scripts\MT-006-vertex-consensus.ps1
#
# PASS CONDITIONS:
#   [x] status = COMPLETED
#   [x] status passed through FINALISING during poll
#   [x] executor present (model, confidence, output, completed_at)
#   [x] review.consensus contains APPROVE
#   [x] review.reviewers = 3 entries, all commitment_verified = true
#   [x] vertex.event_hash is a 64-char lowercase hex SHA-256 string
#   [x] vertex.round >= 1
#   [x] vertex.finalised_at is a valid ISO timestamp

$API_BASE   = "http://localhost:8000/api/v1"
$API_KEY    = "auditex-test-key-phase2"
$MAX_POLLS  = 24      # 24 x 5s = 120s max
$POLL_SLEEP = 5       # seconds between polls

Write-Host ""
Write-Host "======================================================" -ForegroundColor Cyan
Write-Host "  MT-006: Vertex Consensus Layer (Stub Mode)"          -ForegroundColor Cyan
Write-Host "  Phase 5 Manual Test"                                  -ForegroundColor Cyan
Write-Host "======================================================" -ForegroundColor Cyan
Write-Host ""

# -----------------------------------------------------------------------
# STEP 1: Submit task
# -----------------------------------------------------------------------
Write-Host "[1/4] Submitting task..." -ForegroundColor Yellow

$taskBody = @{
    task_type = "document_review"
    payload   = @{
        document        = "MT-006 test: Loan application for Jane Doe. Annual income 65000 GBP. Employed 8 years at Acme Ltd. Requested loan amount 15000 GBP for home improvement. Credit score 742."
        review_criteria = @("completeness", "income_verification", "employment_verification", "risk_assessment")
    }
    metadata  = @{
        submitted_by = "mt-006-test-script"
        workflow_id  = "mt-006-phase5"
    }
} | ConvertTo-Json -Depth 5

try {
    $submitResponse = Invoke-RestMethod `
        -Uri "$API_BASE/tasks" `
        -Method POST `
        -Headers @{ "X-API-Key" = $API_KEY; "Content-Type" = "application/json" } `
        -Body $taskBody
} catch {
    Write-Host "FAIL: Task submission failed: $_" -ForegroundColor Red
    exit 1
}

$taskId = $submitResponse.task_id
Write-Host "  task_id : $taskId" -ForegroundColor Green
Write-Host "  status  : $($submitResponse.status)" -ForegroundColor Green

if ($submitResponse.status -ne "QUEUED") {
    Write-Host "FAIL: Expected status=QUEUED, got $($submitResponse.status)" -ForegroundColor Red
    exit 1
}

# -----------------------------------------------------------------------
# STEP 2: Poll until COMPLETED or FAILED (max 120s)
# -----------------------------------------------------------------------
Write-Host ""
Write-Host "[2/4] Polling task status (max $($MAX_POLLS * $POLL_SLEEP)s)..." -ForegroundColor Yellow

$seenFinalising = $false
$finalResponse  = $null
$pollCount      = 0
$lastStatus     = ""

for ($i = 1; $i -le $MAX_POLLS; $i++) {
    Start-Sleep -Seconds $POLL_SLEEP
    $pollCount++

    try {
        $pollResponse = Invoke-RestMethod `
            -Uri "$API_BASE/tasks/$taskId" `
            -Method GET `
            -Headers @{ "X-API-Key" = $API_KEY }
    } catch {
        Write-Host "  Poll $i : ERROR - $_" -ForegroundColor Red
        continue
    }

    $currentStatus = $pollResponse.status

    if ($currentStatus -ne $lastStatus) {
        $ts = (Get-Date).ToString("HH:mm:ss")
        Write-Host "  [$ts] Poll $i : status = $currentStatus" -ForegroundColor White
        $lastStatus = $currentStatus
    } else {
        Write-Host "  Poll $i : $currentStatus" -ForegroundColor DarkGray
    }

    if ($currentStatus -eq "FINALISING") {
        $seenFinalising = $true
        Write-Host "         ^ FINALISING detected" -ForegroundColor Cyan
    }

    if ($currentStatus -eq "COMPLETED" -or $currentStatus -eq "FAILED") {
        $finalResponse = $pollResponse
        break
    }
}

if ($null -eq $finalResponse) {
    Write-Host ""
    Write-Host "FAIL: Task did not complete within $($MAX_POLLS * $POLL_SLEEP)s" -ForegroundColor Red
    exit 1
}

# -----------------------------------------------------------------------
# STEP 3: Validate final response
# -----------------------------------------------------------------------
Write-Host ""
Write-Host "[3/4] Validating response..." -ForegroundColor Yellow

$pass = $true
$failures = @()

# Helper
function Check($label, $condition, $detail = "") {
    if ($condition) {
        Write-Host "  [PASS] $label" -ForegroundColor Green
    } else {
        Write-Host "  [FAIL] $label$(if ($detail) { ': ' + $detail })" -ForegroundColor Red
        $script:pass = $false
        $script:failures += $label
    }
}

# --- Status checks ---
Check "status = COMPLETED"    ($finalResponse.status -eq "COMPLETED")
Check "FINALISING was observed during polling" $seenFinalising

# --- Executor checks ---
$exec = $finalResponse.executor
Check "executor is present"                   ($null -ne $exec)
Check "executor.model is present"             ($null -ne $exec -and $exec.model -ne $null -and $exec.model -ne "")
Check "executor.confidence is present"        ($null -ne $exec -and $exec.confidence -ne $null)
Check "executor.output is present"            ($null -ne $exec -and $exec.output -ne $null)
Check "executor.completed_at is present"      ($null -ne $exec -and $exec.completed_at -ne $null -and $exec.completed_at -ne "")

# --- Review checks ---
$rev = $finalResponse.review
Check "review is present"                     ($null -ne $rev)
Check "review.consensus contains APPROVE"     ($null -ne $rev -and $rev.consensus -match "APPROVE")
Check "review.reviewers has 3 entries"        ($null -ne $rev -and $rev.reviewers.Count -eq 3)

if ($null -ne $rev -and $rev.reviewers.Count -eq 3) {
    $allVerified = ($rev.reviewers | Where-Object { $_.commitment_verified -eq $true }).Count -eq 3
    Check "all 3 reviewers commitment_verified = true" $allVerified
}

# --- Vertex checks ---
$vtx = $finalResponse.vertex
Check "vertex is present"                     ($null -ne $vtx)

if ($null -ne $vtx) {
    $hash = $vtx.event_hash
    $isValidHash = ($null -ne $hash) -and ($hash -match "^[0-9a-f]{64}$")
    Check "vertex.event_hash is 64-char lowercase hex SHA-256" $isValidHash `
        "got: $hash"

    $round = $vtx.round
    Check "vertex.round >= 1"                 ($null -ne $round -and [int]$round -ge 1) `
        "got: $round"

    $finAt = $vtx.finalised_at
    $isValidTs = ($null -ne $finAt) -and ($finAt -match "^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}")
    Check "vertex.finalised_at is valid ISO timestamp" $isValidTs `
        "got: $finAt"
}

# -----------------------------------------------------------------------
# STEP 4: Print full final response and result
# -----------------------------------------------------------------------
Write-Host ""
Write-Host "[4/4] Final response:" -ForegroundColor Yellow
$finalResponse | ConvertTo-Json -Depth 10 | Write-Host

Write-Host ""
Write-Host "======================================================" -ForegroundColor Cyan

if ($pass) {
    Write-Host "  MT-006 PASS" -ForegroundColor Green
    Write-Host "  All $(($finalResponse | ConvertTo-Json -Depth 10 | Select-String 'PASS').Matches.Count) checks passed." -ForegroundColor Green
    Write-Host "  task_id     : $taskId" -ForegroundColor Green
    Write-Host "  consensus   : $($rev.consensus)" -ForegroundColor Green
    Write-Host "  event_hash  : $($vtx.event_hash)" -ForegroundColor Green
    Write-Host "  round       : $($vtx.round)" -ForegroundColor Green
    Write-Host "  finalised_at: $($vtx.finalised_at)" -ForegroundColor Green
} else {
    Write-Host "  MT-006 FAIL" -ForegroundColor Red
    Write-Host "  Failed checks:" -ForegroundColor Red
    foreach ($f in $failures) {
        Write-Host "    - $f" -ForegroundColor Red
    }
}

Write-Host "======================================================" -ForegroundColor Cyan
Write-Host ""

# =============================================================================
# MT-005: Review Pipeline Complete
# Phase 4 -- Review Layer + GPT-4o + Hash Commitment Scheme
#
# Validates:
#   - Task progresses QUEUED -> EXECUTING -> REVIEWING -> COMPLETED
#   - GET /tasks/{id} returns status=COMPLETED with both executor AND review populated
#   - review.consensus = "3_OF_3_APPROVE" or "2_OF_3_APPROVE"
#   - review.reviewers = array of 3 objects, each with commitment_verified=true
#   - executor.model present
#
# Usage (run directly, not via run.ps1):
#   powershell -ExecutionPolicy Bypass -File docs\testing\manual-test-scripts\MT-005-review-complete.ps1
# =============================================================================

$ErrorActionPreference = "Stop"

$API_BASE    = "http://localhost:8000/api/v1"
$API_KEY     = "auditex-test-key-phase2"
$POLL_EVERY  = 5       # seconds between polls
$MAX_SECONDS = 120     # review adds time vs Phase 3 -- allow up to 2 minutes
$PASS_COUNT  = 0
$FAIL_COUNT  = 0

function Write-Pass($msg) {
    Write-Host "[PASS] $msg" -ForegroundColor Green
    $script:PASS_COUNT++
}
function Write-Fail($msg) {
    Write-Host "[FAIL] $msg" -ForegroundColor Red
    $script:FAIL_COUNT++
}
function Write-Info($msg) {
    Write-Host "[INFO] $msg" -ForegroundColor Cyan
}
function Write-Step($msg) {
    Write-Host ""
    Write-Host "--- $msg ---" -ForegroundColor Yellow
}

# =============================================================================
# STEP 1: Submit task
# =============================================================================
Write-Step "STEP 1: Submit task"

$body = @{
    task_type = "document_review"
    payload   = @{
        document        = "Loan application for Jane Doe. Annual income: 65000 GBP. Employment: Senior Engineer, 7 years. Requested loan amount: 15000 GBP. Purpose: Home improvements. Credit score: 720."
        review_criteria = @("completeness", "income_verification", "employment_verification")
    }
    metadata  = @{
        submitted_by = "MT-005-test-script"
        workflow_id  = "mt-005-review-pipeline-test"
    }
} | ConvertTo-Json -Depth 5

try {
    $submit_response = Invoke-RestMethod `
        -Method POST `
        -Uri "$API_BASE/tasks" `
        -Headers @{ "X-API-Key" = $API_KEY; "Content-Type" = "application/json" } `
        -Body $body
} catch {
    Write-Fail "Task submission failed: $_"
    exit 1
}

$task_id = $submit_response.task_id
$initial_status = $submit_response.status

Write-Info "task_id   = $task_id"
Write-Info "status    = $initial_status"
Write-Info "created   = $($submit_response.created_at)"

if ($task_id -match "^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$") {
    Write-Pass "task_id is a valid UUID"
} else {
    Write-Fail "task_id is not a valid UUID: $task_id"
}

if ($initial_status -eq "QUEUED") {
    Write-Pass "initial status = QUEUED"
} else {
    Write-Fail "initial status expected QUEUED, got: $initial_status"
}

# =============================================================================
# STEP 2: Poll until COMPLETED or FAILED (max $MAX_SECONDS seconds)
# =============================================================================
Write-Step "STEP 2: Polling for completion (max ${MAX_SECONDS}s, polling every ${POLL_EVERY}s)"
Write-Info "Note: Phase 4 adds ~30-60s for 3 reviewer API calls"

$elapsed        = 0
$final_response = $null
$status_history = @()

while ($elapsed -lt $MAX_SECONDS) {
    Start-Sleep -Seconds $POLL_EVERY
    $elapsed += $POLL_EVERY

    try {
        $poll = Invoke-RestMethod `
            -Method GET `
            -Uri "$API_BASE/tasks/$task_id" `
            -Headers @{ "X-API-Key" = $API_KEY }
    } catch {
        Write-Info "Poll error at ${elapsed}s: $_"
        continue
    }

    $current_status = $poll.status
    if ($status_history -notcontains $current_status) {
        $status_history += $current_status
        Write-Info "[${elapsed}s] Status: $current_status"
    }

    if ($current_status -eq "COMPLETED" -or $current_status -eq "FAILED") {
        $final_response = $poll
        break
    }
}

if ($null -eq $final_response) {
    Write-Fail "Task did not reach COMPLETED or FAILED within ${MAX_SECONDS}s"
    Write-Info "Last known status history: $($status_history -join ' -> ')"
    exit 1
}

Write-Info "Status progression: $($status_history -join ' -> ')"

# =============================================================================
# STEP 3: Validate final status
# =============================================================================
Write-Step "STEP 3: Validate final status"

if ($final_response.status -eq "COMPLETED") {
    Write-Pass "status = COMPLETED"
} else {
    Write-Fail "status expected COMPLETED, got: $($final_response.status)"
    Write-Info "Full response: $($final_response | ConvertTo-Json -Depth 10)"
    exit 1
}

if ($status_history -contains "REVIEWING") {
    Write-Pass "Status passed through REVIEWING (review pipeline ran)"
} else {
    Write-Fail "Status never reached REVIEWING -- review pipeline may not have run"
}

# =============================================================================
# STEP 4: Validate executor field
# =============================================================================
Write-Step "STEP 4: Validate executor field"

$executor = $final_response.executor
if ($null -eq $executor) {
    Write-Fail "executor field is null"
} else {
    Write-Pass "executor field is present"

    if ($executor.model -and $executor.model -ne "") {
        Write-Pass "executor.model = $($executor.model)"
    } else {
        Write-Fail "executor.model is missing or empty"
    }

    if ($null -ne $executor.confidence) {
        Write-Pass "executor.confidence = $($executor.confidence)"
    } else {
        Write-Fail "executor.confidence is missing"
    }

    if ($executor.output) {
        Write-Pass "executor.output is present"
    } else {
        Write-Fail "executor.output is missing"
    }

    if ($executor.completed_at) {
        Write-Pass "executor.completed_at = $($executor.completed_at)"
    } else {
        Write-Fail "executor.completed_at is missing"
    }
}

# =============================================================================
# STEP 5: Validate review field
# =============================================================================
Write-Step "STEP 5: Validate review field"

$review = $final_response.review
if ($null -eq $review) {
    Write-Fail "review field is null -- review pipeline did not run or result not stored"
    exit 1
} else {
    Write-Pass "review field is present"
}

$consensus = $review.consensus
if ($consensus -eq "3_OF_3_APPROVE" -or $consensus -eq "2_OF_3_APPROVE") {
    Write-Pass "review.consensus = $consensus"
} else {
    Write-Fail "review.consensus expected 3_OF_3_APPROVE or 2_OF_3_APPROVE, got: $consensus"
}

$reviewers = $review.reviewers
if ($null -eq $reviewers) {
    Write-Fail "review.reviewers is null"
    exit 1
}

$reviewer_count = ($reviewers | Measure-Object).Count
if ($reviewer_count -eq 3) {
    Write-Pass "review.reviewers contains exactly 3 entries"
} else {
    Write-Fail "review.reviewers expected 3 entries, got: $reviewer_count"
}

# =============================================================================
# STEP 6: Validate each reviewer -- commitment_verified, verdict, model
# =============================================================================
Write-Step "STEP 6: Validate each reviewer record"

$idx = 1
foreach ($reviewer in $reviewers) {
    $rmodel   = $reviewer.model
    $rverdict = $reviewer.verdict
    $rconf    = $reviewer.confidence
    $rverified = $reviewer.commitment_verified

    Write-Info "Reviewer ${idx}: model=$rmodel verdict=$rverdict confidence=$rconf commitment_verified=$rverified"

    if ($rmodel -and $rmodel -ne "") {
        Write-Pass "  Reviewer ${idx}: model present = $rmodel"
    } else {
        Write-Fail "  Reviewer ${idx}: model is missing"
    }

    if ($rverdict -eq "APPROVE" -or $rverdict -eq "REJECT") {
        Write-Pass "  Reviewer ${idx}: verdict = $rverdict"
    } else {
        Write-Fail "  Reviewer ${idx}: verdict expected APPROVE or REJECT, got: $rverdict"
    }

    if ($null -ne $rconf) {
        Write-Pass "  Reviewer ${idx}: confidence = $rconf"
    } else {
        Write-Fail "  Reviewer ${idx}: confidence is missing"
    }

    if ($rverified -eq $true) {
        Write-Pass "  Reviewer ${idx}: commitment_verified = true"
    } else {
        Write-Fail "  Reviewer ${idx}: commitment_verified expected true, got: $rverified"
    }

    $idx++
}

# =============================================================================
# STEP 7: Validate review.completed_at
# =============================================================================
Write-Step "STEP 7: Validate review.completed_at"

if ($review.completed_at -and $review.completed_at -ne "") {
    Write-Pass "review.completed_at = $($review.completed_at)"
} else {
    Write-Fail "review.completed_at is missing"
}

# =============================================================================
# SUMMARY
# =============================================================================
Write-Host ""
Write-Host "============================================================" -ForegroundColor White
Write-Host "MT-005 SUMMARY" -ForegroundColor White
Write-Host "============================================================" -ForegroundColor White
Write-Host "PASSED: $PASS_COUNT" -ForegroundColor Green
Write-Host "FAILED: $FAIL_COUNT" -ForegroundColor Red
Write-Host ""

if ($FAIL_COUNT -eq 0) {
    Write-Host "MT-005 RESULT: PASS" -ForegroundColor Green
    Write-Host ""
    Write-Host "Full response:" -ForegroundColor White
    $final_response | ConvertTo-Json -Depth 10
} else {
    Write-Host "MT-005 RESULT: FAIL" -ForegroundColor Red
    Write-Host ""
    Write-Host "Full response for debugging:" -ForegroundColor White
    $final_response | ConvertTo-Json -Depth 10
    exit 1
}

# MT-004: Task Execution Complete
# Phase 3 -- Celery Workers + Claude Execution Layer
#
# PRECONDITIONS:
#   1. Real ANTHROPIC_API_KEY is set in .env
#   2. celery-worker container is running (docker compose up -d)
#   3. auditex-test-key-phase2 API key is active (from Phase 2 seed)
#
# WHAT THIS TEST VALIDATES:
#   - Task submitted via POST /api/v1/tasks
#   - Task auto-progresses: QUEUED -> EXECUTING -> COMPLETED
#   - GET /api/v1/tasks/{id} returns:
#       status = "COMPLETED"
#       executor.model = "claude-sonnet-4-6"
#       executor.output = structured JSON object (document_review schema)
#       executor.confidence = float 0.0-1.0
#
# HOW TO RUN:
#   powershell -ExecutionPolicy Bypass -File run.ps1 -cmd "powershell -ExecutionPolicy Bypass -File docs\testing\manual-test-scripts\MT-004-execution-complete.ps1"
#
# OR run directly:
#   powershell -ExecutionPolicy Bypass -File docs\testing\manual-test-scripts\MT-004-execution-complete.ps1

$API_BASE = "http://localhost:8000/api/v1"
$API_KEY  = "auditex-test-key-phase2"
$MAX_POLL = 12          # 12 polls x 5 seconds = 60 seconds max
$POLL_INTERVAL = 5      # seconds between polls

Write-Host "========================================"
Write-Host "MT-004: Task Execution Complete"
Write-Host "========================================"

# ----------------------------------------------------------
# STEP 1: Submit task
# ----------------------------------------------------------
Write-Host ""
Write-Host "STEP 1: Submitting task..."

$body = @{
    task_type = "document_review"
    payload = @{
        document = "This is a test loan application. Applicant: John Smith. Income: `$50,000. Employment: Employed 5 years. Requested loan: `$10,000."
        review_criteria = @("completeness", "income_verification", "employment_verification")
    }
    metadata = @{
        submitted_by = "MT-004-test-client"
        workflow_id  = "test-wf-mt004"
    }
} | ConvertTo-Json -Depth 5

$headers = @{
    "Content-Type" = "application/json"
    "X-API-Key"    = $API_KEY
}

try {
    $submit_response = Invoke-RestMethod -Uri "$API_BASE/tasks" -Method POST -Headers $headers -Body $body
} catch {
    Write-Host "FAIL: POST /api/v1/tasks failed: $_"
    exit 1
}

$task_id = $submit_response.task_id

Write-Host "  task_id : $task_id"
Write-Host "  status  : $($submit_response.status)"
Write-Host "  message : $($submit_response.message)"

if ($submit_response.status -ne "QUEUED") {
    Write-Host "FAIL: Expected status=QUEUED, got $($submit_response.status)"
    exit 1
}

Write-Host "  STEP 1 PASS: Task submitted and QUEUED"

# ----------------------------------------------------------
# STEP 2: Poll until COMPLETED or FAILED (max 60s)
# ----------------------------------------------------------
Write-Host ""
Write-Host "STEP 2: Polling task status (max ${MAX_POLL} x ${POLL_INTERVAL}s = $($MAX_POLL * $POLL_INTERVAL)s)..."

$final_status = $null
$final_response = $null

for ($i = 1; $i -le $MAX_POLL; $i++) {
    Start-Sleep -Seconds $POLL_INTERVAL

    try {
        $poll = Invoke-RestMethod -Uri "$API_BASE/tasks/$task_id" -Method GET -Headers $headers
    } catch {
        Write-Host "  Poll $i : ERROR - $_"
        continue
    }

    $current_status = $poll.status
    Write-Host "  Poll $i : status=$current_status"

    if ($current_status -eq "COMPLETED" -or $current_status -eq "FAILED") {
        $final_status = $current_status
        $final_response = $poll
        break
    }
}

if (-not $final_status) {
    Write-Host ""
    Write-Host "FAIL: Task did not reach COMPLETED or FAILED within $($MAX_POLL * $POLL_INTERVAL) seconds."
    exit 1
}

# ----------------------------------------------------------
# STEP 3: Validate final response
# ----------------------------------------------------------
Write-Host ""
Write-Host "STEP 3: Validating final response..."
Write-Host ""
Write-Host "--- FULL RESPONSE ---"
$final_response | ConvertTo-Json -Depth 10
Write-Host "--- END RESPONSE ---"
Write-Host ""

$pass = $true

# Check status = COMPLETED
if ($final_status -ne "COMPLETED") {
    Write-Host "FAIL: status = $final_status (expected COMPLETED)"
    Write-Host "      If FAILED, check celery-worker logs: docker compose logs celery-worker"
    $pass = $false
} else {
    Write-Host "  PASS: status = COMPLETED"
}

# Check executor is not null
if (-not $final_response.executor) {
    Write-Host "FAIL: executor field is null"
    $pass = $false
} else {
    # Check executor.model
    $model = $final_response.executor.model
    if ($model -eq "claude-sonnet-4-6" -or $model -like "claude-sonnet*") {
        Write-Host "  PASS: executor.model = $model"
    } else {
        Write-Host "FAIL: executor.model = '$model' (expected claude-sonnet-4-6 or similar)"
        $pass = $false
    }

    # Check executor.output is not null
    if (-not $final_response.executor.output) {
        Write-Host "FAIL: executor.output is null"
        $pass = $false
    } else {
        Write-Host "  PASS: executor.output is present"
        $output = $final_response.executor.output

        # Check document_review specific fields
        if ($null -ne $output.completeness) {
            Write-Host "  PASS: executor.output.completeness = $($output.completeness)"
        } else {
            Write-Host "FAIL: executor.output.completeness is missing"
            $pass = $false
        }

        if ($null -ne $output.recommendation) {
            Write-Host "  PASS: executor.output.recommendation = $($output.recommendation)"
        } else {
            Write-Host "FAIL: executor.output.recommendation is missing"
            $pass = $false
        }

        if ($null -ne $output.reasoning) {
            Write-Host "  PASS: executor.output.reasoning is present"
        } else {
            Write-Host "FAIL: executor.output.reasoning is missing"
            $pass = $false
        }
    }

    # Check executor.confidence is a float
    $confidence = $final_response.executor.confidence
    if ($null -ne $confidence) {
        $conf_float = [double]$confidence
        if ($conf_float -ge 0.0 -and $conf_float -le 1.0) {
            Write-Host "  PASS: executor.confidence = $confidence (valid float 0.0-1.0)"
        } else {
            Write-Host "FAIL: executor.confidence = $confidence (out of range 0.0-1.0)"
            $pass = $false
        }
    } else {
        Write-Host "FAIL: executor.confidence is null"
        $pass = $false
    }
}

# Check review = null (Phase 3 -- review added in Phase 4)
if ($null -eq $final_response.review) {
    Write-Host "  PASS: review = null (expected in Phase 3)"
} else {
    Write-Host "  NOTE: review is not null (unexpected in Phase 3, but not a failure)"
}

# Check vertex = null (Phase 5)
if ($null -eq $final_response.vertex) {
    Write-Host "  PASS: vertex = null (expected in Phase 3)"
}

# Check report_available = false
if ($final_response.report_available -eq $false) {
    Write-Host "  PASS: report_available = false"
}

# ----------------------------------------------------------
# Result
# ----------------------------------------------------------
Write-Host ""
Write-Host "========================================"
if ($pass) {
    Write-Host "MT-004: PASS"
    Write-Host "Phase 3 complete. Ready to commit."
} else {
    Write-Host "MT-004: FAIL"
    Write-Host "Check celery-worker logs: docker compose logs celery-worker --tail=50"
}
Write-Host "========================================"

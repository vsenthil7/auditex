# MT-007 -- PoC Report Generation + EU AI Act Export
# Phase 6 manual test script
#
# PRECONDITIONS:
#   - Real ANTHROPIC_API_KEY in .env
#   - All containers running: docker compose up -d
#   - MT-006 passing (Phase 5 complete)
#   - Celery worker restarted after Phase 6 file changes
#
# HOW TO RUN:
#   powershell -ExecutionPolicy Bypass -File docs\testing\manual-test-scripts\MT-007-reporting.ps1
#
# PASS CONDITIONS (all must be true):
#   [1] Task reaches COMPLETED status
#   [2] report_available = true within 60s of COMPLETED
#   [3] GET /api/v1/reports/{task_id} returns HTTP 200
#   [4] plain_english_summary is a non-empty string
#   [5] eu_ai_act has keys: article_9_risk_management, article_13_transparency, article_17_quality_management
#   [6] vertex_proof.event_hash is a 64-character hex string
#   [7] schema_version = "poc_report_v1"
#   [8] GET /api/v1/reports/{task_id}/export?format=eu_ai_act returns HTTP 200
#   [9] Export has top-level keys: article_9_risk_management, article_13_transparency,
#       article_17_quality_management, plain_english_summary, schema_version

param(
    [string]$ApiKey   = "auditex-test-key-phase2",
    [string]$BaseUrl  = "http://localhost:8000",
    [int]$PollMaxSecs = 120,   # max seconds to wait for COMPLETED
    [int]$ReportMaxSecs = 60   # max extra seconds to wait for report_available
)

$ErrorActionPreference = "Stop"

function Write-Pass  { param($msg) Write-Host "[PASS] $msg" -ForegroundColor Green }
function Write-Fail  { param($msg) Write-Host "[FAIL] $msg" -ForegroundColor Red }
function Write-Info  { param($msg) Write-Host "[INFO] $msg" -ForegroundColor Cyan }
function Write-Step  { param($msg) Write-Host "`n==> $msg" -ForegroundColor Yellow }

$Headers = @{ "X-API-Key" = $ApiKey; "Content-Type" = "application/json" }

# ---------------------------------------------------------------------------
# STEP 1: Submit task
# ---------------------------------------------------------------------------
Write-Step "Submitting task..."

$Body = @{
    task_type = "document_review"
    payload   = @{
        document        = "Loan application. Applicant: Jane Doe. Income: 65000. Employment: 7 years. Loan requested: 15000. Purpose: home improvement."
        review_criteria = @("completeness", "income_verification", "employment_verification")
    }
    metadata  = @{
        submitted_by = "MT-007"
        workflow_id  = "mt007-workflow-001"
    }
} | ConvertTo-Json -Depth 5

$Submit = Invoke-RestMethod -Uri "$BaseUrl/api/v1/tasks" -Method POST `
    -Headers $Headers -Body $Body
$TaskId = $Submit.task_id
Write-Info "task_id = $TaskId"
Write-Info "initial status = $($Submit.status)"

if ($Submit.status -ne "QUEUED") {
    Write-Fail "Expected QUEUED, got $($Submit.status)"
    exit 1
}
Write-Pass "Task submitted with status QUEUED"

# ---------------------------------------------------------------------------
# STEP 2: Poll until COMPLETED
# ---------------------------------------------------------------------------
Write-Step "Polling for COMPLETED (max ${PollMaxSecs}s)..."

$Deadline = (Get-Date).AddSeconds($PollMaxSecs)
$FinalStatus = ""
$LastStatus  = ""

while ((Get-Date) -lt $Deadline) {
    Start-Sleep -Seconds 5
    $Poll = Invoke-RestMethod -Uri "$BaseUrl/api/v1/tasks/$TaskId" -Headers $Headers
    $FinalStatus = $Poll.status

    if ($FinalStatus -ne $LastStatus) {
        Write-Info "Status: $FinalStatus"
        $LastStatus = $FinalStatus
    }

    if ($FinalStatus -eq "COMPLETED" -or $FinalStatus -eq "FAILED") {
        break
    }
}

if ($FinalStatus -ne "COMPLETED") {
    Write-Fail "Task did not reach COMPLETED within ${PollMaxSecs}s. Final status: $FinalStatus"
    exit 1
}
Write-Pass "[1] Task reached COMPLETED"

# ---------------------------------------------------------------------------
# STEP 3: Poll for report_available = true
# ---------------------------------------------------------------------------
Write-Step "Waiting for report_available = true (max ${ReportMaxSecs}s)..."

$ReportDeadline = (Get-Date).AddSeconds($ReportMaxSecs)
$ReportAvailable = $false

while ((Get-Date) -lt $ReportDeadline) {
    Start-Sleep -Seconds 3
    $Poll = Invoke-RestMethod -Uri "$BaseUrl/api/v1/tasks/$TaskId" -Headers $Headers
    if ($Poll.report_available -eq $true) {
        $ReportAvailable = $true
        break
    }
    Write-Info "report_available = $($Poll.report_available) -- waiting..."
}

if (-not $ReportAvailable) {
    Write-Fail "[2] report_available did not become true within ${ReportMaxSecs}s"
    exit 1
}
Write-Pass "[2] report_available = true"

# ---------------------------------------------------------------------------
# STEP 4: GET /api/v1/reports/{task_id}
# ---------------------------------------------------------------------------
Write-Step "Fetching PoC report..."

$Report = Invoke-RestMethod -Uri "$BaseUrl/api/v1/reports/$TaskId" -Headers $Headers
Write-Pass "[3] GET /api/v1/reports/$TaskId returned HTTP 200"

# [4] plain_english_summary non-empty
if ([string]::IsNullOrWhiteSpace($Report.plain_english_summary)) {
    Write-Fail "[4] plain_english_summary is empty"
    exit 1
}
Write-Pass "[4] plain_english_summary is non-empty ($($Report.plain_english_summary.Length) chars)"
Write-Info "Summary preview: $($Report.plain_english_summary.Substring(0, [Math]::Min(120, $Report.plain_english_summary.Length)))..."

# [5] eu_ai_act keys
$EuKeys = @("article_9_risk_management", "article_13_transparency", "article_17_quality_management")
foreach ($Key in $EuKeys) {
    if (-not $Report.eu_ai_act.PSObject.Properties[$Key]) {
        Write-Fail "[5] eu_ai_act missing key: $Key"
        exit 1
    }
}
Write-Pass "[5] eu_ai_act has all required article keys (9, 13, 17)"

# [6] vertex_proof.event_hash is 64-char hex
$EventHash = $Report.vertex_proof.event_hash
if ($EventHash -notmatch '^[0-9a-f]{64}$') {
    Write-Fail "[6] vertex_proof.event_hash is not a 64-char hex string: '$EventHash'"
    exit 1
}
Write-Pass "[6] vertex_proof.event_hash = $EventHash"

# [7] schema_version
if ($Report.schema_version -ne "poc_report_v1") {
    Write-Fail "[7] schema_version expected 'poc_report_v1', got '$($Report.schema_version)'"
    exit 1
}
Write-Pass "[7] schema_version = poc_report_v1"

# ---------------------------------------------------------------------------
# STEP 5: GET /api/v1/reports/{task_id}/export?format=eu_ai_act
# ---------------------------------------------------------------------------
Write-Step "Fetching EU AI Act export..."

$Export = Invoke-RestMethod -Uri "$BaseUrl/api/v1/reports/$TaskId/export?format=eu_ai_act" -Headers $Headers
Write-Pass "[8] GET /api/v1/reports/$TaskId/export?format=eu_ai_act returned HTTP 200"

# [9] Export top-level keys
$ExportKeys = @(
    "article_9_risk_management",
    "article_13_transparency",
    "article_17_quality_management",
    "plain_english_summary",
    "schema_version"
)
foreach ($Key in $ExportKeys) {
    if (-not $Export.PSObject.Properties[$Key]) {
        Write-Fail "[9] Export missing top-level key: $Key"
        exit 1
    }
}
Write-Pass "[9] Export has all required top-level keys"

# ---------------------------------------------------------------------------
# SUMMARY
# ---------------------------------------------------------------------------
Write-Host ""
Write-Host "======================================" -ForegroundColor White
Write-Host " MT-007 RESULT: ALL CHECKS PASSED" -ForegroundColor Green
Write-Host "======================================" -ForegroundColor White
Write-Host " task_id        : $TaskId"
Write-Host " schema_version : $($Report.schema_version)"
Write-Host " event_hash     : $EventHash"
Write-Host " vertex_round   : $($Report.vertex_proof.round)"
Write-Host " generated_at   : $($Report.generated_at)"
Write-Host "======================================" -ForegroundColor White
Write-Host ""

# Print full report JSON for manual inspection
Write-Info "Full report JSON:"
$Report | ConvertTo-Json -Depth 10

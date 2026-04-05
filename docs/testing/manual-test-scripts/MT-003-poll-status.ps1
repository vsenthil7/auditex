# MT-003: Poll Task Status
# TEST ID   : MT-003
# FEATURE   : GET /api/v1/tasks/{task_id}
# PRECONDITIONS: MT-002 passed. last_task_id.txt exists.

$TASK_ID_OVERRIDE = ""

Write-Host "=== MT-003: Poll Task Status ===" -ForegroundColor Cyan

$taskIdFile = "$PSScriptRoot\last_task_id.txt"
if ($TASK_ID_OVERRIDE -ne "") {
    $taskId = $TASK_ID_OVERRIDE
} elseif (Test-Path $taskIdFile) {
    $taskId = (Get-Content $taskIdFile -Raw).Trim()
} else {
    Write-Host "[ERROR] No task_id. Run MT-002 first." -ForegroundColor Red
    exit 1
}

Write-Host "GET /api/v1/tasks/$taskId"

try {
    $wr = Invoke-WebRequest `
        -Uri "http://localhost:8000/api/v1/tasks/$taskId" `
        -Method GET `
        -Headers @{ "X-API-Key" = "auditex-test-key-phase2" } `
        -UseBasicParsing `
        -ErrorAction Stop

    $response = $wr.Content | ConvertFrom-Json
    Write-Host "`nHTTP $($wr.StatusCode)" -ForegroundColor Green
    Write-Host $wr.Content
} catch {
    Write-Host "`n[ERROR] $($_.Exception.Message)" -ForegroundColor Red
    if ($_.Exception.Response) {
        $reader = [System.IO.StreamReader]::new($_.Exception.Response.GetResponseStream())
        Write-Host "Body: $($reader.ReadToEnd())" -ForegroundColor Red
    }
    exit 1
}

# Validation
Write-Host "`n--- VALIDATION ---" -ForegroundColor Yellow
$pass = $true

if ($response.task_id -eq $taskId) {
    Write-Host "[PASS] task_id matches" -ForegroundColor Green
} else {
    Write-Host "[FAIL] task_id mismatch" -ForegroundColor Red; $pass = $false
}

if ($response.status -eq "QUEUED") {
    Write-Host "[PASS] status = QUEUED" -ForegroundColor Green
} else {
    Write-Host "[FAIL] status = '$($response.status)'" -ForegroundColor Red; $pass = $false
}

if ($response.task_type -eq "document_review") {
    Write-Host "[PASS] task_type = document_review" -ForegroundColor Green
} else {
    Write-Host "[FAIL] task_type = '$($response.task_type)'" -ForegroundColor Red; $pass = $false
}

if ($response.workflow_id -eq "test-wf-001") {
    Write-Host "[PASS] workflow_id = test-wf-001" -ForegroundColor Green
} else {
    Write-Host "[FAIL] workflow_id = '$($response.workflow_id)'" -ForegroundColor Red; $pass = $false
}

if ($null -eq $response.executor)       { Write-Host "[PASS] executor = null" -ForegroundColor Green }
if ($null -eq $response.review)         { Write-Host "[PASS] review = null" -ForegroundColor Green }
if ($null -eq $response.vertex)         { Write-Host "[PASS] vertex = null" -ForegroundColor Green }
if ($response.report_available -eq $false) { Write-Host "[PASS] report_available = false" -ForegroundColor Green }

Write-Host "`n=== MT-003 RESULT: $(if ($pass) { 'PASS' } else { 'FAIL' }) ===" -ForegroundColor $(if ($pass) { 'Green' } else { 'Red' })

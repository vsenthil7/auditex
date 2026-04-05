# MT-002: Submit Task
# TEST ID   : MT-002
# FEATURE   : POST /api/v1/tasks
# PRECONDITIONS: MT-001 passed. Seed script run.

Write-Host "=== MT-002: Submit Task ===" -ForegroundColor Cyan

$bodyObj = @{
    task_type = "document_review"
    payload   = @{
        document        = "Test loan application. Applicant: John Smith. Income: 50000."
        review_criteria = @("completeness", "income_verification")
    }
    metadata  = @{
        submitted_by = "test_client"
        workflow_id  = "test-wf-001"
    }
}
$bodyJson = $bodyObj | ConvertTo-Json -Depth 5

Write-Host "POST /api/v1/tasks"

try {
    $wr = Invoke-WebRequest `
        -Uri "http://localhost:8000/api/v1/tasks" `
        -Method POST `
        -Headers @{ "X-API-Key" = "auditex-test-key-phase2"; "Content-Type" = "application/json" } `
        -Body $bodyJson `
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

$taskId = $response.task_id
$taskId | Out-File -FilePath "$PSScriptRoot\last_task_id.txt" -Encoding utf8
Write-Host "`n[INFO] task_id saved: $taskId" -ForegroundColor Yellow

# Validation
Write-Host "`n--- VALIDATION ---" -ForegroundColor Yellow
$pass = $true

$uuidRegex = '^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$'
if ($taskId -match $uuidRegex) {
    Write-Host "[PASS] task_id is valid UUID" -ForegroundColor Green
} else {
    Write-Host "[FAIL] task_id not a valid UUID: '$taskId'" -ForegroundColor Red
    $pass = $false
}

if ($response.status -eq "QUEUED") {
    Write-Host "[PASS] status = QUEUED" -ForegroundColor Green
} else {
    Write-Host "[FAIL] status = '$($response.status)'" -ForegroundColor Red
    $pass = $false
}

if ($response.created_at) {
    Write-Host "[PASS] created_at = $($response.created_at)" -ForegroundColor Green
} else {
    Write-Host "[FAIL] created_at missing" -ForegroundColor Red
    $pass = $false
}

Write-Host "`n=== MT-002 RESULT: $(if ($pass) { 'PASS' } else { 'FAIL' }) ===" -ForegroundColor $(if ($pass) { 'Green' } else { 'Red' })

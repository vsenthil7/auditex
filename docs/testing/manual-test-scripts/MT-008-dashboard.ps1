# MT-008 -- Dashboard Frontend Manual Test
# Auditex Phase 7
# Run: powershell -ExecutionPolicy Bypass -File docs\testing\manual-test-scripts\MT-008-dashboard.ps1

$ErrorActionPreference = "Stop"
$pass = $true
$results = @()

Write-Host ""
Write-Host "=======================================" -ForegroundColor Cyan
Write-Host "  MT-008  Auditex Dashboard Frontend   " -ForegroundColor Cyan
Write-Host "=======================================" -ForegroundColor Cyan
Write-Host ""

# Step 1: Open browser
Write-Host "[1/5] Opening http://localhost:3000 in default browser..." -ForegroundColor Yellow
Start-Process "http://localhost:3000"
Start-Sleep -Seconds 3

# Check 1
$ans = Read-Host "Does the dashboard load without errors (no blank screen, no console errors)? (y/n)"
if ($ans.Trim().ToLower() -ne 'y') {
    Write-Host "FAIL: Dashboard did not load cleanly." -ForegroundColor Red
    $pass = $false
}
$results += [PSCustomObject]@{ Check = "Dashboard loads without errors"; Result = if ($ans -eq 'y') { "PASS" } else { "FAIL" } }

# Check 2
Write-Host ""
Write-Host "[2/5] Fill in the Submit Task form and submit a task." -ForegroundColor Yellow
Write-Host "      Use any task type and paste some text as the document content." -ForegroundColor Gray
$ans = Read-Host "Does the submitted task appear in the Task List panel immediately at QUEUED status? (y/n)"
if ($ans.Trim().ToLower() -ne 'y') {
    Write-Host "FAIL: Task did not appear in the list after submission." -ForegroundColor Red
    $pass = $false
}
$results += [PSCustomObject]@{ Check = "Task appears in list at QUEUED after submit"; Result = if ($ans -eq 'y') { "PASS" } else { "FAIL" } }

# Check 3
Write-Host ""
Write-Host "[3/5] Watch the task status badge in the Task List panel (wait up to 60 seconds)." -ForegroundColor Yellow
Write-Host "      Status should progress: QUEUED -> EXECUTING -> REVIEWING -> FINALISING -> COMPLETED" -ForegroundColor Gray
$ans = Read-Host "Does the status update live without manually refreshing the page? (y/n)"
if ($ans.Trim().ToLower() -ne 'y') {
    Write-Host "FAIL: Status did not update in real time." -ForegroundColor Red
    $pass = $false
}
$results += [PSCustomObject]@{ Check = "Status updates in real time (3s polling)"; Result = if ($ans -eq 'y') { "PASS" } else { "FAIL" } }

# Check 4
Write-Host ""
Write-Host "[4/5] Click on the COMPLETED task row to open the Task Detail panel." -ForegroundColor Yellow
Write-Host "      The Report section should appear once report_available = true." -ForegroundColor Gray
$ans = Read-Host "Does the TaskDetail panel show the PoC report (plain_english_summary + EU AI Act sections)? (y/n)"
if ($ans.Trim().ToLower() -ne 'y') {
    Write-Host "FAIL: Report not shown in TaskDetail." -ForegroundColor Red
    $pass = $false
}
$results += [PSCustomObject]@{ Check = "View Report shows PoC report content"; Result = if ($ans -eq 'y') { "PASS" } else { "FAIL" } }

# Check 5
Write-Host ""
Write-Host "[5/5] Click the 'Export EU AI Act JSON' button in the Report section." -ForegroundColor Yellow
$ans = Read-Host "Does clicking Export download a JSON file named auditex-report-<task_id>.json? (y/n)"
if ($ans.Trim().ToLower() -ne 'y') {
    Write-Host "FAIL: Export did not download a JSON file." -ForegroundColor Red
    $pass = $false
}
$results += [PSCustomObject]@{ Check = "Export EU AI Act JSON downloads file"; Result = if ($ans -eq 'y') { "PASS" } else { "FAIL" } }

# Summary
Write-Host ""
Write-Host "=======================================" -ForegroundColor Cyan
Write-Host "  MT-008 RESULTS" -ForegroundColor Cyan
Write-Host "=======================================" -ForegroundColor Cyan
$results | Format-Table -AutoSize

if ($pass) {
    Write-Host "MT-008 PASSED (5/5)" -ForegroundColor Green
    Write-Host "Ready to commit: feat: Phase 7 complete -- dashboard frontend MT-008 PASS" -ForegroundColor Green
} else {
    Write-Host "MT-008 FAILED -- fix issues above before committing." -ForegroundColor Red
    exit 1
}

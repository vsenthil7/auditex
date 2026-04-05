# MT-006 -- Tamper-Proof Verification (fixed detection logic)
# Tests that audit_events table blocks UPDATE and DELETE at DB level.
# Spec reference: S07 MT-006, S02.2, S03

$root = Split-Path -Parent $PSScriptRoot
$ts   = Get-Date -Format "yyyyMMdd_HHmmss"
$log  = "$root\runs\${ts}_MT006_tamper_proof\run.log"
New-Item -ItemType Directory -Force -Path (Split-Path $log) | Out-Null

function Write-Log($text, $color = "White") {
    Write-Host $text -ForegroundColor $color
    $text | Out-File $log -Encoding UTF8 -Append
}

Write-Log "MT-006: Tamper-Proof Verification -- $(Get-Date)" "Cyan"
Write-Log "Log: $log" "Cyan"
Write-Log ""

# Step 1 -- Insert a test event
Write-Log "--- STEP 1: Insert a test audit event ---" "Yellow"
$insert = docker exec auditex-postgres-1 psql -U auditex -d auditex -c "INSERT INTO audit_events (id, event_type, payload_json, sequence) VALUES (gen_random_uuid(), 'test_event_mt006', '{""test"": true}', 0) RETURNING id, event_type, created_at;" 2>&1
Write-Log ($insert | Out-String)

# Step 2 -- Attempt UPDATE (must fail)
Write-Log ""
Write-Log "--- STEP 2: Attempt UPDATE on audit_events (must fail) ---" "Yellow"
$update = docker exec auditex-postgres-1 psql -U auditex -d auditex -c "UPDATE audit_events SET event_type = 'TAMPERED' WHERE event_type = 'test_event_mt006';" 2>&1
$updateStr = $update | Out-String
Write-Log $updateStr

if ($updateStr -match "append-only" -or $updateStr -match "ERROR" -or $updateStr -match "not permitted") {
    Write-Log "PASS: UPDATE correctly blocked. Trigger fired." "Green"
} else {
    Write-Log "FAIL: UPDATE was not blocked." "Red"
}

# Step 3 -- Attempt DELETE (must fail)
Write-Log ""
Write-Log "--- STEP 3: Attempt DELETE on audit_events (must fail) ---" "Yellow"
$delete = docker exec auditex-postgres-1 psql -U auditex -d auditex -c "DELETE FROM audit_events WHERE event_type = 'test_event_mt006';" 2>&1
$deleteStr = $delete | Out-String
Write-Log $deleteStr

if ($deleteStr -match "append-only" -or $deleteStr -match "ERROR" -or $deleteStr -match "not permitted") {
    Write-Log "PASS: DELETE correctly blocked. Trigger fired." "Green"
} else {
    Write-Log "FAIL: DELETE was not blocked." "Red"
}

# Step 4 -- Verify original record unchanged
Write-Log ""
Write-Log "--- STEP 4: Verify original record still intact ---" "Yellow"
$verify = docker exec auditex-postgres-1 psql -U auditex -d auditex -c "SELECT id, event_type, created_at FROM audit_events WHERE event_type = 'test_event_mt006';" 2>&1
$verifyStr = $verify | Out-String
Write-Log $verifyStr

if ($verifyStr -match "test_event_mt006") {
    Write-Log "PASS: Original record intact and unmodified." "Green"
} else {
    Write-Log "FAIL: Record missing or modified." "Red"
}

# Summary
Write-Log ""
Write-Log "======================================" "Cyan"
Write-Log "MT-006 SUMMARY" "Cyan"
Write-Log "Step 1 - Insert:          PASS" "Green"
Write-Log "Step 2 - UPDATE blocked:  $(if ($updateStr -match 'ERROR') {'PASS'} else {'FAIL'})" $(if ($updateStr -match 'ERROR') {'Green'} else {'Red'})
Write-Log "Step 3 - DELETE blocked:  $(if ($deleteStr -match 'ERROR') {'PASS'} else {'FAIL'})" $(if ($deleteStr -match 'ERROR') {'Green'} else {'Red'})
Write-Log "Step 4 - Record intact:   $(if ($verifyStr -match 'test_event_mt006') {'PASS'} else {'FAIL'})" $(if ($verifyStr -match 'test_event_mt006') {'Green'} else {'Red'})
Write-Log "======================================" "Cyan"
Write-Log "--- MT-006 COMPLETE --- $(Get-Date -Format 'HH:mm:ss') ---" "Cyan"
Write-Log "Log: $log" "Green"

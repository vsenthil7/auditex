# Auditex -- Test db_clear_queue.sql end to end
# Runs from project root:
#   powershell -ExecutionPolicy Bypass -File backend\scripts\test_db_clear_queue.ps1
#
# What it does:
#   1. Show current status
#   2. Insert 2 fake stuck tasks (10min + 15min old)
#   3. Confirm they exist (active should be 2)
#   4. Run db_clear_queue.sql via pipe
#   5. Confirm active = 0 after clear
#   6. Clean up test tasks
#   7. Confirm clean state
#   All output written to runs\test_db_clear_queue_<timestamp>.log

$root    = Split-Path -Parent (Split-Path -Parent $PSScriptRoot)
$ts      = Get-Date -Format "yyyyMMdd_HHmmss"
$logDir  = Join-Path $root "runs"
$logFile = Join-Path $logDir "test_db_clear_queue_$ts.log"

function Log($msg) {
    $line = "[$(Get-Date -Format 'HH:mm:ss')] $msg"
    Write-Host $line
    $line | Out-File $logFile -Encoding UTF8 -Append
}

function RunSQL($label, $sql) {
    Log ">> $label"
    $out = docker compose exec postgres psql -U auditex -d auditex -c $sql 2>&1
    foreach ($line in $out) { Log "   $line" }
    Log ""
    return $out
}

New-Item -ItemType Directory -Force -Path $logDir | Out-Null

Log "======================================================"
Log "  TEST: db_clear_queue.sql"
Log "  Log: $logFile"
Log "======================================================"
Log ""

# 1. Current status before test
RunSQL "BEFORE: Status counts" "SELECT status, COUNT(*) FROM tasks GROUP BY status ORDER BY COUNT(*) DESC"
RunSQL "BEFORE: Active count" "SELECT COUNT(*) as active FROM tasks WHERE status IN ('QUEUED','EXECUTING','REVIEWING','FINALISING')"

# 2. Insert 2 fake stuck tasks
Log ">> CREATING 2 FAKE STUCK TASKS (10min + 15min old)..."
$insertSQL = "INSERT INTO tasks (id, task_type, status, payload_json, created_at) VALUES (gen_random_uuid(), 'document_review', 'QUEUED', '{""test"":true}', NOW() - INTERVAL '10 minutes'), (gen_random_uuid(), 'risk_analysis', 'EXECUTING', '{""test"":true}', NOW() - INTERVAL '15 minutes')"
$out = docker compose exec postgres psql -U auditex -d auditex -c $insertSQL 2>&1
foreach ($line in $out) { Log "   $line" }
Log ""

# 3. Confirm stuck tasks exist
RunSQL "AFTER INSERT: Active count (expect 2)" "SELECT COUNT(*) as active FROM tasks WHERE status IN ('QUEUED','EXECUTING','REVIEWING','FINALISING')"
RunSQL "AFTER INSERT: Stuck tasks detail" "SELECT LEFT(id::text,8) AS id, task_type, status, ROUND(EXTRACT(EPOCH FROM (NOW()-created_at))/60)::int AS age_min FROM tasks WHERE status IN ('QUEUED','EXECUTING','REVIEWING','FINALISING') ORDER BY created_at ASC"

# 4. Run db_clear_queue.sql via PowerShell pipe
Log ">> RUNNING db_clear_queue.sql..."
$sqlFile = Join-Path $root "backend\scripts\db_clear_queue.sql"
$out = Get-Content $sqlFile | docker compose exec -T postgres psql -U auditex -d auditex 2>&1
foreach ($line in $out) { Log "   $line" }
Log ""

# 5. Confirm active = 0
RunSQL "AFTER CLEAR: Active count (expect 0)" "SELECT COUNT(*) as active FROM tasks WHERE status IN ('QUEUED','EXECUTING','REVIEWING','FINALISING')"
RunSQL "AFTER CLEAR: Status counts" "SELECT status, COUNT(*) FROM tasks GROUP BY status ORDER BY COUNT(*) DESC"

# 6. Clean up test tasks (delete the fake ones we inserted)
Log ">> CLEANING UP test tasks..."
$cleanSQL = "DELETE FROM tasks WHERE payload_json = '{""test"":true}' AND failure_reason = 'Force-failed by db_clear_queue.sql'"
$out = docker compose exec postgres psql -U auditex -d auditex -c $cleanSQL 2>&1
foreach ($line in $out) { Log "   $line" }
Log ""

# 7. Final state
RunSQL "FINAL: Status counts" "SELECT status, COUNT(*) FROM tasks GROUP BY status ORDER BY COUNT(*) DESC"
RunSQL "FINAL: Active count (must be 0)" "SELECT COUNT(*) as active FROM tasks WHERE status IN ('QUEUED','EXECUTING','REVIEWING','FINALISING')"

Log "======================================================"
Log "  TEST COMPLETE"
Log "  Share this log: $logFile"
Log "======================================================"

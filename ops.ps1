# Auditex -- Master Operations Script
# Handles: git commits, db status, db clear, playwright tests
# All output shown on screen AND saved to runs\ops_<timestamp>.log
#
# Usage:
#   powershell -ExecutionPolicy Bypass -File ops.ps1 -action git    -msg "your commit message"
#   powershell -ExecutionPolicy Bypass -File ops.ps1 -action status
#   powershell -ExecutionPolicy Bypass -File ops.ps1 -action clear
#   powershell -ExecutionPolicy Bypass -File ops.ps1 -action test
#   powershell -ExecutionPolicy Bypass -File ops.ps1 -action playwright
#   powershell -ExecutionPolicy Bypass -File ops.ps1 -action all     -msg "your commit message"

param(
    [string]$action = "status",
    [string]$msg    = ""
)

# ── Setup ──────────────────────────────────────────────────────────────────────
$root = "C:\Users\v_sen\Documents\Projects\0001_Hack0014_Vertex_Swarm_Tashi\auditex"
Set-Location $root

$ts      = Get-Date -Format "yyyyMMdd_HHmmss"
$logDir  = Join-Path $root "runs"
$logFile = Join-Path $logDir "ops_${action}_${ts}.log"
New-Item -ItemType Directory -Force -Path $logDir | Out-Null

# ── Helpers ────────────────────────────────────────────────────────────────────
function Log($msg, $color = "White") {
    $line = "[$(Get-Date -Format 'HH:mm:ss')] $msg"
    Write-Host $line -ForegroundColor $color
    $line | Out-File $logFile -Encoding UTF8 -Append
}

function Banner($title) {
    Log ""
    Log "============================================================" "Cyan"
    Log "  $title" "Cyan"
    Log "============================================================" "Cyan"
}

function Run($cmd) {
    Log "> $cmd" "Yellow"
    $out = Invoke-Expression $cmd 2>&1
    foreach ($line in $out) {
        Log "  $line"
    }
    Log ""
    return $out
}

function SQL($label, $sql) {
    Log ">> $label" "Yellow"
    $out = docker compose exec postgres psql -U auditex -d auditex -c $sql 2>&1
    foreach ($line in $out) {
        if ($line -notmatch "level=warning") { Log "  $line" }
    }
    Log ""
    return $out
}

# ── Actions ────────────────────────────────────────────────────────────────────

function Do-Git {
    if ($msg -eq "") {
        Log "ERROR: -msg required for git action. Example:" "Red"
        Log '  powershell -ExecutionPolicy Bypass -File ops.ps1 -action git -msg "your message"' "Red"
        exit 1
    }
    Banner "GIT COMMIT"
    Log "1) date" "Cyan"
    Log (Get-Date -Format "dd/MM/yyyy HH:mm:ss")
    Log ""
    Log "2) git status" "Cyan"
    Run "git status"
    Log "3) git add -A" "Cyan"
    Run "powershell -ExecutionPolicy Bypass -File run.ps1 -cmd 'git add -A'"
    Log "4) git status" "Cyan"
    Run "git status"
    Log "5) git commit" "Cyan"
    Run "git commit -m `"$msg`""
    Log "6) git status" "Cyan"
    Run "git status"
    Log "7) date" "Cyan"
    Log (Get-Date -Format "dd/MM/yyyy HH:mm:ss")
    Log ""
    Log "DONE: Git commit complete" "Green"
}

function Do-Status {
    Banner "DB STATUS"
    SQL "Status counts"  "SELECT status, COUNT(*) FROM tasks GROUP BY status ORDER BY COUNT(*) DESC"
    SQL "Active pipeline" "SELECT COUNT(*) as active FROM tasks WHERE status IN ('QUEUED','EXECUTING','REVIEWING','FINALISING')"
    SQL "Last 10 tasks"  "SELECT LEFT(id::text,8) AS id, task_type, status, to_char(created_at,'HH24:MI') AS time, report_available AS rpt, CASE WHEN executor_output_json IS NOT NULL THEN 'Y' ELSE 'N' END AS ex, CASE WHEN review_result_json IS NOT NULL THEN 'Y' ELSE 'N' END AS rev FROM tasks ORDER BY created_at DESC LIMIT 10"
    SQL "Reports"        "SELECT COUNT(*) as report_count FROM reports"
    Log "DONE: Status shown above. Log: $logFile" "Green"
}

function Do-Clear {
    Banner "CLEAR STUCK QUEUE"

    Log "BEFORE clear:" "Yellow"
    SQL "Active count" "SELECT COUNT(*) as active FROM tasks WHERE status IN ('QUEUED','EXECUTING','REVIEWING','FINALISING')"
    SQL "Stuck tasks"  "SELECT LEFT(id::text,8) AS id, task_type, status, ROUND(EXTRACT(EPOCH FROM (NOW()-created_at))/60)::int AS age_min FROM tasks WHERE status IN ('QUEUED','EXECUTING','REVIEWING','FINALISING') AND created_at < NOW() - INTERVAL '5 minutes' ORDER BY created_at ASC"

    Log "CLEARING..." "Yellow"
    SQL "UPDATE" "UPDATE tasks SET status='FAILED', failure_reason='Force-failed by ops.ps1' WHERE status IN ('QUEUED','EXECUTING','REVIEWING','FINALISING') AND created_at < NOW() - INTERVAL '5 minutes'"

    Log "AFTER clear:" "Yellow"
    SQL "Status counts"  "SELECT status, COUNT(*) FROM tasks GROUP BY status ORDER BY COUNT(*) DESC"
    SQL "Active count (must be 0)" "SELECT COUNT(*) as active FROM tasks WHERE status IN ('QUEUED','EXECUTING','REVIEWING','FINALISING')"

    Log "DONE: Queue cleared. Log: $logFile" "Green"
}

function Do-Test {
    Banner "TEST db_clear_queue (stuck scenario)"

    Log "STEP 1: Current state" "Yellow"
    SQL "Before" "SELECT status, COUNT(*) FROM tasks GROUP BY status ORDER BY COUNT(*) DESC"

    Log "STEP 2: Insert 2 fake stuck tasks" "Yellow"
    SQL "Insert" "INSERT INTO tasks (id, task_type, status, payload_json, created_at) VALUES (gen_random_uuid(), 'document_review', 'QUEUED', '{""test"":true}', NOW() - INTERVAL '10 minutes'), (gen_random_uuid(), 'risk_analysis', 'EXECUTING', '{""test"":true}', NOW() - INTERVAL '15 minutes')"

    Log "STEP 3: Confirm 2 stuck tasks exist" "Yellow"
    SQL "Active (expect 2)" "SELECT COUNT(*) as active FROM tasks WHERE status IN ('QUEUED','EXECUTING','REVIEWING','FINALISING')"

    Log "STEP 4: Run clear" "Yellow"
    SQL "Clear" "UPDATE tasks SET status='FAILED', failure_reason='Force-failed by ops.ps1' WHERE status IN ('QUEUED','EXECUTING','REVIEWING','FINALISING') AND created_at < NOW() - INTERVAL '5 minutes'"

    Log "STEP 5: Confirm active = 0" "Yellow"
    $out = SQL "Active (expect 0)" "SELECT COUNT(*) as active FROM tasks WHERE status IN ('QUEUED','EXECUTING','REVIEWING','FINALISING')"
    $active = ($out | Where-Object { $_ -match "^\s+\d+" } | Select-Object -First 1) -replace '\s',''
    if ($active -eq "0") {
        Log "PASS: active = 0. Script works correctly." "Green"
    } else {
        Log "FAIL: active = $active. Check output above." "Red"
    }

    Log "STEP 6: Cleanup test tasks" "Yellow"
    SQL "Delete test tasks" "DELETE FROM tasks WHERE payload_json = '{""test"":true}'"

    Log "STEP 7: Final state" "Yellow"
    SQL "Final counts" "SELECT status, COUNT(*) FROM tasks GROUP BY status ORDER BY COUNT(*) DESC"

    Log "DONE: Test complete. Log: $logFile" "Green"
}

function Do-Playwright {
    Banner "PLAYWRIGHT TESTS"

    Log "STEP 1: Check queue before running" "Yellow"
    $out = SQL "Active count" "SELECT COUNT(*) as active FROM tasks WHERE status IN ('QUEUED','EXECUTING','REVIEWING','FINALISING')"
    $active = ($out | Where-Object { $_ -match "^\s+\d+" } | Select-Object -First 1) -replace '\s',''

    if ($active -ne "0") {
        Log "Queue has $active active task(s). Clearing before Playwright..." "Yellow"
        SQL "Clear" "UPDATE tasks SET status='FAILED', failure_reason='Force-failed by ops.ps1' WHERE status IN ('QUEUED','EXECUTING','REVIEWING','FINALISING') AND created_at < NOW() - INTERVAL '5 minutes'"
        SQL "Active after clear (must be 0)" "SELECT COUNT(*) as active FROM tasks WHERE status IN ('QUEUED','EXECUTING','REVIEWING','FINALISING')"
    } else {
        Log "Queue is clear. Proceeding to Playwright." "Green"
    }

    Log "STEP 2: Run Playwright tests" "Yellow"
    $frontendDir = Join-Path $root "frontend"
    Set-Location $frontendDir
    Log "> cd $frontendDir" "Yellow"
    Log "> npx playwright test --reporter=list" "Yellow"
    Log ""

    & npx playwright test --reporter=list 2>&1 | Tee-Object -FilePath $logFile -Append

    Set-Location $root
    Log ""
    Log "DONE: Playwright complete. Log: $logFile" "Green"
}

# ── Dispatch ───────────────────────────────────────────────────────────────────
Log ""
Log "ops.ps1  action=$action  $(Get-Date -Format 'dd/MM/yyyy HH:mm:ss')" "Cyan"
Log "Log: $logFile" "Cyan"
Log ""

switch ($action) {
    "git"        { Do-Git }
    "status"     { Do-Status }
    "clear"      { Do-Clear }
    "test"       { Do-Test }
    "playwright" { Do-Playwright }
    "all"        {
        Do-Git
        Do-Clear
        Do-Playwright
    }
    default {
        Log "Unknown action: $action" "Red"
        Log "Valid actions: git, status, clear, test, playwright, all" "Yellow"
    }
}

# Auditex -- Master Operations Script
# All output shown on screen AND saved to runs\ops_<action>_<timestamp>.log
# Claude reads the log file directly — no need to paste output.
#
# Usage:
#   powershell -ExecutionPolicy Bypass -File ops.ps1 -action git        -msg "commit message"
#   powershell -ExecutionPolicy Bypass -File ops.ps1 -action status
#   powershell -ExecutionPolicy Bypass -File ops.ps1 -action clear
#   powershell -ExecutionPolicy Bypass -File ops.ps1 -action celery-logs
#   powershell -ExecutionPolicy Bypass -File ops.ps1 -action docker-ps
#   powershell -ExecutionPolicy Bypass -File ops.ps1 -action git-log
#   powershell -ExecutionPolicy Bypass -File ops.ps1 -action diag       (celery+db+docker+git all at once)
#   powershell -ExecutionPolicy Bypass -File ops.ps1 -action test
#   powershell -ExecutionPolicy Bypass -File ops.ps1 -action playwright
#   powershell -ExecutionPolicy Bypass -File ops.ps1 -action all        -msg "commit message"

param(
    [string]$action = "status",
    [string]$msg    = ""
)

$root = "C:\Users\v_sen\Documents\Projects\0001_Hack0014_Vertex_Swarm_Tashi\auditex"
Set-Location $root

$ts      = Get-Date -Format "yyyyMMdd_HHmmss"
$logDir  = Join-Path $root "runs"
$logFile = Join-Path $logDir "ops_${action}_${ts}.log"
New-Item -ItemType Directory -Force -Path $logDir | Out-Null

function Log($msg, $color = "White") {
    $line = "[$(Get-Date -Format 'HH:mm:ss')] $msg"
    Write-Host $line -ForegroundColor $color
    $line | Out-File $logFile -Encoding UTF8 -Append
}
function Banner($title) {
    Log ""; Log "============================================================" "Cyan"
    Log "  $title" "Cyan"; Log "============================================================" "Cyan"
}
function Run($cmd) {
    Log "> $cmd" "Yellow"
    $out = Invoke-Expression $cmd 2>&1
    foreach ($line in $out) { Log "  $line" }
    Log ""; return $out
}
function SQL($label, $sql) {
    Log ">> $label" "Yellow"
    $out = docker compose exec postgres psql -U auditex -d auditex -c $sql 2>&1
    foreach ($line in $out) { if ($line -notmatch "level=warning") { Log "  $line" } }
    Log ""; return $out
}
function CeleryLogs($lines = 100) {
    Log ">> Celery worker last $lines lines" "Yellow"
    $out = docker compose logs celery-worker --tail $lines 2>&1
    foreach ($line in $out) { if ($line -notmatch "level=warning") { Log "  $line" } }
    Log ""
}

# ── GIT ────────────────────────────────────────────────────────────────────────
function Do-Git {
    if ($msg -eq "") { Log "ERROR: -msg required. Example: -msg `"your message`"" "Red"; exit 1 }
    Banner "GIT COMMIT"
    Log "1) date" "Cyan"; Log (Get-Date -Format "dd/MM/yyyy HH:mm:ss"); Log ""

    Log "2) git status" "Cyan"; Run "git status"

    Log "3) git diff - reviewing all changes" "Cyan"
    $statusLines = git status --porcelain 2>&1
    foreach ($entry in $statusLines) {
        if ($entry.Length -lt 3) { continue }
        $flag = $entry.Substring(0,2).Trim()
        $file = $entry.Substring(3).Trim()
        Log "---- diff: $file [$flag] ----" "Yellow"
        if ($flag -eq "??") {
            Log "  (untracked new file - no diff available until staged)" "Yellow"
        } else {
            $diffOut = & git diff -- $file 2>&1
            foreach ($dl in $diffOut) { Log "  $dl" }
        }
        Log ""
    }

    Log "4) REVIEW COMPLETE - waiting for your confirmation" "Cyan"
    $confirm = Read-Host "Type Y to proceed with git add + commit, N to abort"
    Log "   User entered: $confirm" "Yellow"
    if ($confirm -ne "Y") {
        Log "ABORTED by user. Nothing staged or committed." "Red"
        return
    }

    Log "5) git add -A (via run.ps1 audit wrapper)" "Cyan"
    Run "powershell -ExecutionPolicy Bypass -File run.ps1 -cmd 'git add -A'"

    Log "6) git status" "Cyan"; Run "git status"

    Log "7) git commit" "Cyan"; Run "git commit -m `"$msg`""

    Log "8) git status" "Cyan"; Run "git status"

    Log "9) date" "Cyan"; Log (Get-Date -Format "dd/MM/yyyy HH:mm:ss"); Log ""
    Log "DONE: Git commit complete. Log: $logFile" "Green"
}

# ── DB STATUS ──────────────────────────────────────────────────────────────────
function Do-Status {
    Banner "DB STATUS"
    SQL "Task status counts"  "SELECT status, COUNT(*) FROM tasks GROUP BY status ORDER BY COUNT(*) DESC"
    SQL "Active in pipeline"  "SELECT COUNT(*) as active FROM tasks WHERE status IN ('QUEUED','EXECUTING','REVIEWING','FINALISING')"
    SQL "Last 10 tasks"       "SELECT LEFT(id::text,8) AS id, task_type, status, to_char(created_at,'HH24:MI') AS time, report_available AS rpt, CASE WHEN executor_output_json IS NOT NULL THEN 'Y' ELSE 'N' END AS ex, CASE WHEN review_result_json IS NOT NULL THEN 'Y' ELSE 'N' END AS rev FROM tasks ORDER BY created_at DESC LIMIT 10"
    SQL "Reports"             "SELECT COUNT(*) as report_count FROM reports"
    CeleryLogs 20
    Log "DONE: Status complete. Log: $logFile" "Green"
}

# ── CLEAR STUCK QUEUE ──────────────────────────────────────────────────────────
function Do-Clear {
    Banner "CLEAR STUCK QUEUE"
    Log "BEFORE:" "Yellow"
    SQL "Active count" "SELECT COUNT(*) as active FROM tasks WHERE status IN ('QUEUED','EXECUTING','REVIEWING','FINALISING')"
    SQL "Stuck tasks"  "SELECT LEFT(id::text,8) AS id, task_type, status, ROUND(EXTRACT(EPOCH FROM (NOW()-created_at))/60)::int AS age_min FROM tasks WHERE status IN ('QUEUED','EXECUTING','REVIEWING','FINALISING') AND created_at < NOW() - INTERVAL '5 minutes' ORDER BY created_at ASC"
    Log "CLEARING..." "Yellow"
    SQL "UPDATE" "UPDATE tasks SET status='FAILED', failure_reason='Force-failed by ops.ps1' WHERE status IN ('QUEUED','EXECUTING','REVIEWING','FINALISING') AND created_at < NOW() - INTERVAL '5 minutes'"
    Log "AFTER:" "Yellow"
    SQL "Status counts"            "SELECT status, COUNT(*) FROM tasks GROUP BY status ORDER BY COUNT(*) DESC"
    SQL "Active count (must be 0)" "SELECT COUNT(*) as active FROM tasks WHERE status IN ('QUEUED','EXECUTING','REVIEWING','FINALISING')"
    Log "DONE: Queue cleared. Log: $logFile" "Green"
}

# ── CELERY LOGS ────────────────────────────────────────────────────────────────
function Do-CeleryLogs {
    Banner "CELERY WORKER LOGS (last 100 lines)"
    CeleryLogs 100
    Log "DONE: Celery logs captured. Log: $logFile" "Green"
}

# ── DOCKER PS ─────────────────────────────────────────────────────────────────
function Do-DockerPs {
    Banner "DOCKER CONTAINER STATUS"
    Log ">> docker compose ps" "Yellow"
    $out = docker compose ps 2>&1
    foreach ($line in $out) { if ($line -notmatch "level=warning") { Log "  $line" } }
    Log ""
    Log ">> docker stats (snapshot)" "Yellow"
    $out = docker stats --no-stream --format "table {{.Name}}\t{{.CPUPerc}}\t{{.MemUsage}}\t{{.MemPerc}}" 2>&1
    foreach ($line in $out) { Log "  $line" }
    Log ""
    Log "DONE: Docker status captured. Log: $logFile" "Green"
}

# ── GIT LOG ───────────────────────────────────────────────────────────────────
function Do-GitLog {
    Banner "GIT LOG (last 15 commits)"
    Run "git log --oneline -15"
    Log "DONE: Git log captured. Log: $logFile" "Green"
}

# ── DIAG (everything in one shot) ─────────────────────────────────────────────
function Do-Diag {
    Banner "FULL DIAGNOSTIC"
    Log "Running: git-log + docker-ps + db-status + celery-logs" "Cyan"
    Log ""

    Log "=== GIT LOG ===" "Cyan"
    Run "git log --oneline -10"

    Log "=== DOCKER PS ===" "Cyan"
    $out = docker compose ps 2>&1
    foreach ($line in $out) { if ($line -notmatch "level=warning") { Log "  $line" } }
    Log ""
    $out = docker stats --no-stream --format "table {{.Name}}\t{{.CPUPerc}}\t{{.MemUsage}}\t{{.MemPerc}}" 2>&1
    foreach ($line in $out) { Log "  $line" }
    Log ""

    Log "=== DB STATUS ===" "Cyan"
    SQL "Task status counts"  "SELECT status, COUNT(*) FROM tasks GROUP BY status ORDER BY COUNT(*) DESC"
    SQL "Active in pipeline"  "SELECT COUNT(*) as active FROM tasks WHERE status IN ('QUEUED','EXECUTING','REVIEWING','FINALISING')"
    SQL "Last 10 tasks"       "SELECT LEFT(id::text,8) AS id, task_type, status, to_char(created_at,'HH24:MI') AS time, report_available AS rpt, CASE WHEN executor_output_json IS NOT NULL THEN 'Y' ELSE 'N' END AS ex, CASE WHEN review_result_json IS NOT NULL THEN 'Y' ELSE 'N' END AS rev FROM tasks ORDER BY created_at DESC LIMIT 10"
    SQL "Reports"             "SELECT COUNT(*) as report_count FROM reports"

    Log "=== CELERY LOGS (last 50) ===" "Cyan"
    CeleryLogs 50

    Log "DONE: Full diagnostic complete. Log: $logFile" "Green"
}

# ── TEST db_clear_queue ────────────────────────────────────────────────────────
function Do-Test {
    Banner "TEST db_clear_queue (stuck scenario)"
    Log "STEP 1: Current state" "Yellow"
    SQL "Before" "SELECT status, COUNT(*) FROM tasks GROUP BY status ORDER BY COUNT(*) DESC"
    Log "STEP 2: Insert 2 fake stuck tasks" "Yellow"
    SQL "Insert" "INSERT INTO tasks (id, task_type, status, payload_json, created_at) VALUES (gen_random_uuid(), 'document_review', 'QUEUED', '{""test"":true}', NOW() - INTERVAL '10 minutes'), (gen_random_uuid(), 'risk_analysis', 'EXECUTING', '{""test"":true}', NOW() - INTERVAL '15 minutes')"
    Log "STEP 3: Confirm 2 stuck" "Yellow"
    SQL "Active (expect 2)" "SELECT COUNT(*) as active FROM tasks WHERE status IN ('QUEUED','EXECUTING','REVIEWING','FINALISING')"
    Log "STEP 4: Run clear" "Yellow"
    SQL "Clear" "UPDATE tasks SET status='FAILED', failure_reason='Force-failed by ops.ps1' WHERE status IN ('QUEUED','EXECUTING','REVIEWING','FINALISING') AND created_at < NOW() - INTERVAL '5 minutes'"
    Log "STEP 5: Confirm active = 0" "Yellow"
    $out = SQL "Active (expect 0)" "SELECT COUNT(*) as active FROM tasks WHERE status IN ('QUEUED','EXECUTING','REVIEWING','FINALISING')"
    $active = ($out | Where-Object { $_ -match "^\s+\d+" } | Select-Object -First 1) -replace '\s',''
    if ($active -eq "0") { Log "PASS: active = 0" "Green" } else { Log "FAIL: active = $active" "Red" }
    Log "STEP 6: Cleanup" "Yellow"
    SQL "Delete test tasks" "DELETE FROM tasks WHERE payload_json = '{""test"":true}'"
    Log "STEP 7: Final state" "Yellow"
    SQL "Final counts" "SELECT status, COUNT(*) FROM tasks GROUP BY status ORDER BY COUNT(*) DESC"
    Log "DONE: Test complete. Log: $logFile" "Green"
}

# ── PLAYWRIGHT ────────────────────────────────────────────────────────────────
function Do-Playwright {
    Banner "PLAYWRIGHT TESTS"

    Log "STEP 1: Clear stuck queue" "Yellow"
    SQL "Active before" "SELECT COUNT(*) as active FROM tasks WHERE status IN ('QUEUED','EXECUTING','REVIEWING','FINALISING')"
    SQL "Clear stuck" "UPDATE tasks SET status='FAILED', failure_reason='Force-failed by ops.ps1' WHERE status IN ('QUEUED','EXECUTING','REVIEWING','FINALISING') AND created_at < NOW() - INTERVAL '5 minutes'"
    SQL "Active after clear (must be 0)" "SELECT COUNT(*) as active FROM tasks WHERE status IN ('QUEUED','EXECUTING','REVIEWING','FINALISING')"

    Log "STEP 2: Restart Celery worker (clean state)" "Yellow"
    $out = docker compose restart celery-worker 2>&1
    foreach ($line in $out) { if ($line -notmatch "level=warning") { Log "  $line" } }
    Log "  Waiting 8s for worker to come back up..."
    Start-Sleep -Seconds 8
    Log "  Celery restarted" "Green"
    Log ""

    Log "STEP 3: Confirm Celery is running" "Yellow"
    CeleryLogs 15

    Log "STEP 4: Run Playwright tests" "Yellow"
    $frontendDir = Join-Path $root "frontend"
    Set-Location $frontendDir
    Log "> cd $frontendDir" "Yellow"
    Log "> npx playwright test --reporter=list" "Yellow"
    Log ""
    & npx playwright test --reporter=list 2>&1 | Tee-Object -FilePath $logFile -Append

    Set-Location $root
    Log ""

    Log "STEP 5: Celery logs after tests" "Yellow"
    CeleryLogs 50

    Log "STEP 6: DB status after tests" "Yellow"
    SQL "Final task counts" "SELECT status, COUNT(*) FROM tasks GROUP BY status ORDER BY COUNT(*) DESC"
    SQL "Active pipeline"   "SELECT COUNT(*) as active FROM tasks WHERE status IN ('QUEUED','EXECUTING','REVIEWING','FINALISING')"

    Log "DONE: Playwright complete. Log: $logFile" "Green"
}

# ── Dispatch ───────────────────────────────────────────────────────────────────
Log ""
Log "ops.ps1  action=$action  $(Get-Date -Format 'dd/MM/yyyy HH:mm:ss')" "Cyan"
Log "Log: $logFile" "Cyan"
Log ""

switch ($action) {
    "git"         { Do-Git }
    "status"      { Do-Status }
    "clear"       { Do-Clear }
    "celery-logs" { Do-CeleryLogs }
    "docker-ps"   { Do-DockerPs }
    "git-log"     { Do-GitLog }
    "diag"        { Do-Diag }
    "test"        { Do-Test }
    "playwright"  { Do-Playwright }
    "all"         { Do-Git; Do-Clear; Do-Playwright }
    default       {
        Log "Unknown action: '$action'" "Red"
        Log "Valid actions: git, status, clear, celery-logs, docker-ps, git-log, diag, test, playwright, all" "Yellow"
    }
}

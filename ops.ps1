# Auditex -- Master Operations Script
# All output shown on screen AND saved to runs\ops_<action>_<timestamp>.log
# Claude reads the log file directly -- no need to paste output.
#
# Usage:
#   powershell -ExecutionPolicy Bypass -File ops.ps1 -action git                -msg "commit message"
#   powershell -ExecutionPolicy Bypass -File ops.ps1 -action commit-auto        -msg "commit message"  (non-interactive)
#   powershell -ExecutionPolicy Bypass -File ops.ps1 -action git-push
#   powershell -ExecutionPolicy Bypass -File ops.ps1 -action git-remote-add     -msg "https://github.com/user/repo.git"
#   powershell -ExecutionPolicy Bypass -File ops.ps1 -action git-push-upstream
#   powershell -ExecutionPolicy Bypass -File ops.ps1 -action status
#   powershell -ExecutionPolicy Bypass -File ops.ps1 -action clear
#   powershell -ExecutionPolicy Bypass -File ops.ps1 -action celery-logs
#   powershell -ExecutionPolicy Bypass -File ops.ps1 -action foxmq-logs
#   powershell -ExecutionPolicy Bypass -File ops.ps1 -action docker-ps
#   powershell -ExecutionPolicy Bypass -File ops.ps1 -action git-log
#   powershell -ExecutionPolicy Bypass -File ops.ps1 -action diag               (celery+db+docker+git all at once)
#   powershell -ExecutionPolicy Bypass -File ops.ps1 -action test
#   powershell -ExecutionPolicy Bypass -File ops.ps1 -action pytest
#   powershell -ExecutionPolicy Bypass -File ops.ps1 -action vitest
#   powershell -ExecutionPolicy Bypass -File ops.ps1 -action playwright
#   powershell -ExecutionPolicy Bypass -File ops.ps1 -action all                -msg "commit message"

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
function FoxMQLogs($lines = 100) {
    Log ">> FoxMQ broker last $lines lines" "Yellow"
    $out = docker compose logs foxmq --tail $lines 2>&1
    foreach ($line in $out) { Log "  $line" }
    Log ""
}

# == GIT (interactive, user confirmation required) ============================
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

# == COMMIT-AUTO (non-interactive, for shell-MCP use) =========================
function Do-CommitAuto {
    if ($msg -eq "") { Log "ERROR: -msg required. Example: -msg `"[TAG] message`"" "Red"; exit 1 }
    Banner "GIT COMMIT (AUTO - no interactive prompt)"
    Log "1) date" "Cyan"; Log (Get-Date -Format "dd/MM/yyyy HH:mm:ss"); Log ""

    Log "2) git status (pre)" "Cyan"; Run "git status"

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

    Log "4) git add -A" "Cyan"; Run "git add -A"

    Log "5) git status (staged)" "Cyan"; Run "git status"

    Log "6) git commit -m ""$msg""" "Cyan"
    $out = & git commit -m $msg 2>&1
    $exit = $LASTEXITCODE
    foreach ($line in $out) { Log "  $line" }
    Log ""

    if ($exit -ne 0) {
        Log "ERROR: git commit failed with exit code $exit" "Red"
        Log "DONE (FAILED): Log: $logFile" "Red"
        exit $exit
    }

    Log "7) git status (post)" "Cyan"; Run "git status"
    Log "8) git log -1" "Cyan"; Run "git log --oneline -1"

    Log "9) date" "Cyan"; Log (Get-Date -Format "dd/MM/yyyy HH:mm:ss"); Log ""
    Log "DONE: Commit-auto complete. Log: $logFile" "Green"
}

# == GIT-PUSH =================================================================
function Do-GitPush {
    Banner "GIT PUSH"
    Log "1) git status (pre-push)" "Cyan"; Run "git status"
    Log "2) git log -3" "Cyan"; Run "git log --oneline -3"
    Log "3) git push" "Cyan"
    $out = & git push 2>&1
    $exit = $LASTEXITCODE
    foreach ($line in $out) { Log "  $line" }
    Log ""
    if ($exit -ne 0) {
        Log "ERROR: git push failed with exit code $exit" "Red"
        Log "DONE (FAILED): Log: $logFile" "Red"
        exit $exit
    }
    Log "4) git status (post-push)" "Cyan"; Run "git status"
    Log "DONE: Git push complete. Log: $logFile" "Green"
}

# == GIT REMOTE ADD ===========================================================
function Do-GitRemoteAdd {
    if ($msg -eq "") { Log "ERROR: -msg required (used as remote URL)." "Red"; exit 1 }
    Banner "GIT REMOTE ADD origin"
    Log "1) existing remotes" "Cyan"; Run "git remote -v"
    Log "2) git remote add origin $msg" "Cyan"
    $out = & git remote add origin $msg 2>&1
    $exit = $LASTEXITCODE
    foreach ($line in $out) { Log "  $line" }
    Log ""
    if ($exit -ne 0) {
        Log "ERROR: git remote add failed with exit code $exit" "Red"
        Log "DONE (FAILED): Log: $logFile" "Red"
        exit $exit
    }
    Log "3) confirm remote" "Cyan"; Run "git remote -v"
    Log "DONE: Remote added. Log: $logFile" "Green"
}

# == GIT PUSH UPSTREAM (first push to set upstream) ===========================
function Do-GitPushUpstream {
    Banner "GIT PUSH --set-upstream origin main"
    Log "1) git status" "Cyan"; Run "git status"
    Log "2) git log -5" "Cyan"; Run "git log --oneline -5"
    Log "3) git remote -v" "Cyan"; Run "git remote -v"
    Log "4) git push --set-upstream origin main" "Cyan"
    $out = & git push --set-upstream origin main 2>&1
    $exit = $LASTEXITCODE
    foreach ($line in $out) { Log "  $line" }
    Log ""
    if ($exit -ne 0) {
        Log "ERROR: git push --set-upstream failed with exit code $exit" "Red"
        Log "DONE (FAILED): Log: $logFile" "Red"
        exit $exit
    }
    Log "5) git status (post-push)" "Cyan"; Run "git status"
    Log "DONE: Upstream set and pushed. Log: $logFile" "Green"
}

# == DB STATUS ================================================================
function Do-Status {
    Banner "DB STATUS"
    SQL "Task status counts"  "SELECT status, COUNT(*) FROM tasks GROUP BY status ORDER BY COUNT(*) DESC"
    SQL "Active in pipeline"  "SELECT COUNT(*) as active FROM tasks WHERE status IN ('QUEUED','EXECUTING','REVIEWING','FINALISING')"
    SQL "Last 10 tasks"       "SELECT LEFT(id::text,8) AS id, task_type, status, to_char(created_at,'HH24:MI') AS time, report_available AS rpt, CASE WHEN executor_output_json IS NOT NULL THEN 'Y' ELSE 'N' END AS ex, CASE WHEN review_result_json IS NOT NULL THEN 'Y' ELSE 'N' END AS rev FROM tasks ORDER BY created_at DESC LIMIT 10"
    SQL "Reports"             "SELECT COUNT(*) as report_count FROM reports"
    CeleryLogs 20
    Log "DONE: Status complete. Log: $logFile" "Green"
}

# == CLEAR STUCK QUEUE ========================================================
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

# == CELERY LOGS ==============================================================
function Do-CeleryLogs {
    Banner "CELERY WORKER LOGS (last 100 lines)"
    CeleryLogs 100
    Log "DONE: Celery logs captured. Log: $logFile" "Green"
}

# == FOXMQ LOGS ===============================================================
function Do-FoxMQLogs {
    Banner "FOXMQ BROKER LOGS (last 100 lines)"
    FoxMQLogs 100
    Log "DONE: FoxMQ logs captured. Log: $logFile" "Green"
}

# == DOCKER PS ================================================================
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

# == GIT LOG ==================================================================
function Do-GitLog {
    Banner "GIT LOG (last 15 commits)"
    Run "git log --oneline -15"
    Log "DONE: Git log captured. Log: $logFile" "Green"
}

# == DIAG (everything in one shot) ============================================
function Do-Diag {
    Banner "FULL DIAGNOSTIC"
    Log "Running: git-log + docker-ps + db-status + celery-logs + foxmq-logs" "Cyan"
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

    Log "=== FOXMQ LOGS (last 30) ===" "Cyan"
    FoxMQLogs 30

    Log "DONE: Full diagnostic complete. Log: $logFile" "Green"
}

# == TEST db_clear_queue ======================================================
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

# == PYTEST (backend unit + integration) ======================================
function Do-Pytest {
    Banner "PYTEST -- backend test suite (inside api container)"

    Log "STEP 1: Confirm api container running" "Yellow"
    $psOut = docker compose ps --services --status running 2>&1
    foreach ($line in $psOut) { Log "  $line" }
    $running = $psOut -join " "
    if ($running -notmatch "\bapi\b") {
        Log "ERROR: api container is not running. Start with 'docker compose up -d'" "Red"
        Log "DONE (FAILED): Log: $logFile" "Red"
        exit 1
    }
    Log "  api container: running" "Green"
    Log ""

    Log "STEP 2: Run pytest with coverage" "Yellow"
    Log "> docker compose exec -T api pytest tests/ -v --tb=short --cov=. --cov-report=term-missing --cov-report=html:tests/coverage_html --cov-fail-under=100" "Yellow"
    Log ""
    & docker compose exec -T api pytest tests/ -v --tb=short --cov=. --cov-report=term-missing --cov-report=html:tests/coverage_html --cov-fail-under=100 2>&1 | Tee-Object -FilePath $logFile -Append
    $pytestExit = $LASTEXITCODE
    Log ""
    Log "pytest exit code: $pytestExit" "Cyan"

    if ($pytestExit -eq 0) {
        Log "PASS: pytest 100% coverage achieved" "Green"
    } else {
        Log "FAIL: pytest exit code $pytestExit (tests failed OR coverage below 100%)" "Red"
    }

    Log "DONE: pytest complete. Log: $logFile" "Green"
    exit $pytestExit
}

# == VITEST (frontend unit + component) =======================================
function Do-Vitest {
    Banner "VITEST -- frontend component tests"

    $frontendDir = Join-Path $root "frontend"
    Set-Location $frontendDir
    Log "> cd $frontendDir" "Yellow"

    Log "STEP 1: npm install (ensure vitest + testing-library installed)" "Yellow"
    Log "> npm install" "Yellow"
    & npm install 2>&1 | Tee-Object -FilePath $logFile -Append
    Log ""

    Log "STEP 2: Run vitest with coverage" "Yellow"
    Log "> npx vitest run --coverage" "Yellow"
    Log ""
    & npx vitest run --coverage 2>&1 | Tee-Object -FilePath $logFile -Append
    $vitestExit = $LASTEXITCODE
    Log ""
    Log "vitest exit code: $vitestExit" "Cyan"

    Set-Location $root

    if ($vitestExit -eq 0) {
        Log "PASS: vitest suite green" "Green"
    } else {
        Log "FAIL: vitest exit code $vitestExit" "Red"
    }

    Log "DONE: vitest complete. Log: $logFile" "Green"
    exit $vitestExit
}

# == PLAYWRIGHT ===============================================================
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

# == GIT PUSH FORCE UPSTREAM (overwrites remote main) ========================
function Do-GitPushForceUpstream {
    Banner "GIT PUSH --force-with-lease --set-upstream origin main"
    Log "1) git status" "Cyan"; Run "git status"
    Log "2) git log -5" "Cyan"; Run "git log --oneline -5"
    Log "3) git remote -v" "Cyan"; Run "git remote -v"
    Log "4) git push --force-with-lease --set-upstream origin main" "Cyan"
    $out = & git push --force-with-lease --set-upstream origin main 2>&1
    $exit = $LASTEXITCODE
    foreach ($line in $out) { Log "  $line" }
    Log ""
    if ($exit -ne 0) {
        Log "ERROR: git push --force failed with exit code $exit" "Red"
        Log "DONE (FAILED): Log: $logFile" "Red"
        exit $exit
    }
    Log "5) git status (post-push)" "Cyan"; Run "git status"
    Log "DONE: Force-upstream push complete. Log: $logFile" "Green"
}

# == Dispatch =================================================================
Log ""
Log "ops.ps1  action=$action  $(Get-Date -Format 'dd/MM/yyyy HH:mm:ss')" "Cyan"
Log "Log: $logFile" "Cyan"
Log ""

switch ($action) {
    "git"               { Do-Git }
    "commit-auto"       { Do-CommitAuto }
    "git-push"          { Do-GitPush }
    "git-remote-add"    { Do-GitRemoteAdd }
    "git-push-upstream" { Do-GitPushUpstream }
    "git-push-force-upstream" { Do-GitPushForceUpstream }
    "status"            { Do-Status }
    "clear"             { Do-Clear }
    "celery-logs"       { Do-CeleryLogs }
    "foxmq-logs"        { Do-FoxMQLogs }
    "docker-ps"         { Do-DockerPs }
    "git-log"           { Do-GitLog }
    "diag"              { Do-Diag }
    "test"              { Do-Test }
    "pytest"            { Do-Pytest }
    "vitest"            { Do-Vitest }
    "playwright"        { Do-Playwright }
    "all"               { Do-Git; Do-Clear; Do-Playwright }
    default             {
        Log "Unknown action: '$action'" "Red"
        Log "Valid actions: git, commit-auto, git-push, git-remote-add, git-push-upstream, git-push-force-upstream, status, clear, celery-logs, foxmq-logs, docker-ps, git-log, diag, test, pytest, vitest, playwright, all" "Yellow"
    }
}

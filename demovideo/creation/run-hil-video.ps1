# Phase 14: Create demo video v4 with HIL block (Article 14 H-1..H-12).
# Mirrors run-creation.ps1 but writes output as end-to-end-v4-{timestamp}.webm
# so v3 (pre-HIL) and v4 (post-HIL) are clearly distinguished in demo/ + demo/_backup/.
#
# This is the runner the PHASE-14 build prompt asks for. It wraps the same playwright spec
# (frontend/tests/demo/end-to-end-demo.spec.ts) which now includes the 12 HIL beats.
#
# Usage:
#   .\demovideo\creation\run-hil-video.ps1

$ErrorActionPreference = 'Continue'
$here = Split-Path -Parent $MyInvocation.MyCommand.Path
$projectRoot = Split-Path -Parent (Split-Path -Parent $here)
$demoDir = Join-Path $projectRoot 'demo'
$backupDir = Join-Path $demoDir '_backup'
$resultsDir = Join-Path (Split-Path -Parent $here) 'results\creation'
$specPath = 'tests/demo/end-to-end-demo.spec.ts'

Write-Host '' -ForegroundColor Yellow
Write-Host '[hil-video] === Auditex Demo Video v4 Creation (with HIL Article 14) ===' -ForegroundColor Yellow

# 1) Pre-flight: containers up?
Write-Host '[hil-video] 1/5 pre-flight: docker compose ps' -ForegroundColor Cyan
Push-Location $projectRoot
try {
    $ps = & docker compose ps --format '{{.Name}}:{{.Status}}' 2>$null
    if (-not ($ps -match 'auditex-frontend.*Up')) { throw 'frontend container not up - run: docker compose up -d' }
    if (-not ($ps -match 'auditex-api.*Up')) { throw 'api container not up' }
    if (-not ($ps -match 'auditex-celery-worker.*Up')) { throw 'celery-worker container not up - HIL finalise worker required' }
    Write-Host '  containers OK (frontend + api + celery-worker)'
} finally { Pop-Location }

# 1b) HIL pre-flight: confirm policies seeded so contract_check flips to AWAITING_HUMAN_REVIEW
Write-Host '[hil-video] 1b) HIL pre-flight: alembic 0005 policies' -ForegroundColor Cyan
$policyRows = docker exec auditex-postgres-1 psql -U auditex -d auditex -tA -c "SELECT count(*) FROM human_oversight_policies WHERE required = true;"
if ($policyRows -lt 3) { throw 'HIL policies not seeded; expected 3 required rows, found ' + $policyRows }
Write-Host ('  policies OK (' + $policyRows.Trim() + ' required rows)')

# 1c) HIL pre-flight: clean stale AWAITING_HUMAN_REVIEW so the demo flow does not pick up an old task
Write-Host '[hil-video] 1c) HIL pre-flight: clean stale AWAITING_HUMAN_REVIEW tasks' -ForegroundColor Cyan
docker exec auditex-postgres-1 psql -U auditex -d auditex -c "UPDATE tasks SET status='COMPLETED' WHERE status='AWAITING_HUMAN_REVIEW';" | Out-Null
docker exec auditex-postgres-1 psql -U auditex -d auditex -c "DELETE FROM human_decisions;" | Out-Null
Write-Host '  stale data cleaned'

# 2) Rate-limit safety check (recreate already done at session start)
Write-Host '[hil-video] 2/5 rate-limit safety check' -ForegroundColor Cyan
Write-Host '  (assumed bumped via .env RATE_LIMIT_PER_MINUTE=600 + container recreate)'

# 3) Run the playwright spec - HIL block runs after the 3 outcome paths
Write-Host '[hil-video] 3/5 running playwright spec (DEMO=1) - this includes HIL block H-1..H-12' -ForegroundColor Cyan
Write-Host '  Expected runtime: ~12-15 min (3 outcome paths + HIL Article 14 walkthrough)' -ForegroundColor Gray
$frontendDir = Join-Path $projectRoot 'frontend'
Push-Location $frontendDir
try {
    $env:DEMO = '1'
    npx playwright test $specPath --headed --project=chromium --reporter=line
    if ($LASTEXITCODE -ne 0) { Write-Host '[hil-video] playwright spec failed - aborting archive' -ForegroundColor Red; exit $LASTEXITCODE }
} finally { Remove-Item Env:DEMO -ErrorAction SilentlyContinue; Pop-Location }

# 4) Archive recorded video as v4 (clearly distinguished from v3 pre-HIL)
Write-Host '[hil-video] 4/5 archiving v4 video to demo/ + demo/_backup/' -ForegroundColor Cyan
New-Item -Path $demoDir -ItemType Directory -Force | Out-Null
New-Item -Path $backupDir -ItemType Directory -Force | Out-Null
New-Item -Path $resultsDir -ItemType Directory -Force | Out-Null
$src = Get-ChildItem (Join-Path $frontendDir 'test-results') -Recurse -Filter 'video.webm' | Where-Object { $_.FullName -match 'end-to-end' } | Sort-Object LastWriteTime -Descending | Select-Object -First 1
if (-not $src) { Write-Host '[hil-video] no recorded video found - did the spec run?' -ForegroundColor Red; exit 1 }
$stamp = Get-Date -Format 'yyyyMMdd_HHmmss'
$dstName = 'end-to-end-v4-' + $stamp + '.webm'
$dstMain = Join-Path $demoDir $dstName
$dstBackup = Join-Path $backupDir $dstName
Copy-Item $src.FullName $dstMain -Force
Copy-Item $src.FullName $dstBackup -Force
# Write pointer for verify-a/b to pick up
Set-Content -Path (Join-Path $resultsDir 'latest.txt') -Value $dstMain -Encoding ASCII
Write-Host (' active : ' + $dstMain)
Write-Host (' backup : ' + $dstBackup)
Write-Host (' size   : ' + [math]::Round($src.Length/1MB, 2) + ' MB')

# 5) Done
Write-Host '[hil-video] 5/5 complete' -ForegroundColor Green
Write-Host '  watch with: start ' -NoNewline; Write-Host $dstMain
Write-Host '' -ForegroundColor Yellow
Write-Host 'Next: run verification-a (.\demovideo\run.ps1 -action verify-a) then verification-b (-action verify-b)' -ForegroundColor Yellow
$global:LATEST_DEMO_VIDEO = $dstMain

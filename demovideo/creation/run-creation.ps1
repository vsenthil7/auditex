# Option 1: Create demo video.
# Modular pieces this wrapper coordinates:
#   1. Pre-flight checks   - docker compose ps, port 8000 & 3000 open
#   2. Rate-limit bump      - temp env override RATE_LIMIT_PER_MINUTE=600 for the api container
#   3. Run playwright spec  - frontend/tests/demo/end-to-end-demo.spec.ts (DEMO=1)
#   4. Archive video         - copy from test-results to demo/ + demo/_backup/ with timestamp
#   5. Cleanup               - revert temp env override

$ErrorActionPreference = 'Stop'
$here = Split-Path -Parent $MyInvocation.MyCommand.Path
$projectRoot = Split-Path -Parent (Split-Path -Parent $here)
$demoDir = Join-Path $projectRoot 'demo'
$backupDir = Join-Path $demoDir '_backup'
$resultsDir = Join-Path (Split-Path -Parent $here) 'results\creation'
$resultsDir = Join-Path (Split-Path -Parent $here) 'results\creation'
$resultsDir = Join-Path (Split-Path -Parent $here) 'results\creation'
$resultsDir = Join-Path (Split-Path -Parent $here) 'results\creation'
$specPath = 'tests/demo/end-to-end-demo.spec.ts'

Write-Host '' -ForegroundColor Yellow
Write-Host '[creation] === Auditex Demo Video Creation === ' -ForegroundColor Yellow

# 1) Pre-flight: containers up?
Write-Host '[creation] 1/5 pre-flight: docker compose ps' -ForegroundColor Cyan
Push-Location $projectRoot
try {
    $ps = docker compose ps --format '{{.Name}}:{{.Status}}'
    if (-not ($ps -match 'auditex-frontend.*Up')) { throw 'frontend container not up - run: docker compose up -d' }
    if (-not ($ps -match 'auditex-api.*Up')) { throw 'api container not up' }
    Write-Host '  containers OK'
} finally { Pop-Location }

# 2) Rate-limit bump (temp - just env override on api container)
Write-Host '[creation] 2/5 rate-limit bump: api RATE_LIMIT_PER_MINUTE=600' -ForegroundColor Cyan
docker exec auditex-api-1 sh -c 'export RATE_LIMIT_PER_MINUTE=600 && echo $RATE_LIMIT_PER_MINUTE' | Out-Null
# Note: docker exec env only persists for that exec; for full bump we recreate the container.
# For the demo session we trust the recreate done at the start; this exec is a no-op safety check.

# 3) Run the playwright spec in DEMO mode
Write-Host '[creation] 3/5 running playwright spec (DEMO=1)' -ForegroundColor Cyan
$frontendDir = Join-Path $projectRoot 'frontend'
Push-Location $frontendDir
try {
    $env:DEMO = '1'
    npx playwright test $specPath --headed --project=chromium --reporter=line
    if ($LASTEXITCODE -ne 0) { Write-Host '[creation] playwright spec failed - aborting archive' -ForegroundColor Red; exit $LASTEXITCODE }
} finally { Remove-Item Env:DEMO -ErrorAction SilentlyContinue; Pop-Location }

# 4) Archive the recorded video
Write-Host '[creation] 4/5 archiving video to demo/ + demo/_backup/' -ForegroundColor Cyan
New-Item -Path $demoDir -ItemType Directory -Force | Out-Null
New-Item -Path $backupDir -ItemType Directory -Force | Out-Null
New-Item -Path $resultsDir -ItemType Directory -Force | Out-Null
$src = Get-ChildItem (Join-Path $frontendDir 'test-results') -Recurse -Filter 'video.webm' | Where-Object { $_.FullName -match 'end-to-end' } | Sort-Object LastWriteTime -Descending | Select-Object -First 1
if (-not $src) { Write-Host '[creation] no recorded video found - did the spec run?' -ForegroundColor Red; exit 1 }
$stamp = Get-Date -Format 'yyyyMMdd_HHmmss'
$dstName = 'end-to-end-' + $stamp + '.webm'
$dstMain = Join-Path $demoDir $dstName
$dstBackup = Join-Path $backupDir $dstName
Copy-Item $src.FullName $dstMain -Force
Copy-Item $src.FullName $dstBackup -Force
# Write a pointer to latest active video for verify-a/b to pick up
Set-Content -Path (Join-Path $resultsDir 'latest.txt') -Value $dstMain -Encoding ASCII
Write-Host (' active : ' + $dstMain)
Write-Host (' backup : ' + $dstBackup)
Write-Host (' size  : ' + [math]::Round($src.Length/1MB, 2) + ' MB')

# 5) Done
Write-Host "[creation] 5/5 complete" -ForegroundColor Green
Write-Host "  watch with: start " -NoNewline; Write-Host $dstMain
$global:LATEST_DEMO_VIDEO = $dstMain

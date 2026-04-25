# Option A: Structural review - re-runs the demo flow with hard assertions per scene gate.
# Output: pass/fail per scene printed to console + saved as a JUnit report.

$ErrorActionPreference = 'Stop'
$here = Split-Path -Parent $MyInvocation.MyCommand.Path
$projectRoot = Split-Path -Parent (Split-Path -Parent $here)
$frontendDir = Join-Path $projectRoot 'frontend'
$reportDir = Join-Path (Split-Path -Parent $here) 'results\verification-a'
New-Item -Path $reportDir -ItemType Directory -Force | Out-Null

# Copy spec into the project tests folder so playwright picks it up via the project config.
$specSrc = Join-Path $here 'structural-review.spec.ts'
$specDst = Join-Path $frontendDir 'tests\demo\structural-review.spec.ts'
Copy-Item $specSrc $specDst -Force

Write-Host '' -ForegroundColor Yellow
Write-Host '[verify-a] === Structural review (Option A) === ' -ForegroundColor Yellow

Push-Location $frontendDir
try {
    $stamp = Get-Date -Format 'yyyyMMdd_HHmmss'
    $reportFile = Join-Path $reportDir (('structural-review-' + $stamp + '.txt'))
    npx playwright test tests/demo/structural-review.spec.ts --project=chromium --reporter=line 2>&1 | Tee-Object -FilePath $reportFile
    Write-Host '' -ForegroundColor Green
    Write-Host ('[verify-a] report saved -> ' + $reportFile) -ForegroundColor Green
} finally { Pop-Location }

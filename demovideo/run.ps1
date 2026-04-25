# Demo video pipeline wrapper - one entry point, three sub-pipelines.
# Each sub-pipeline lives in its own folder (creation/, verification-a/, verification-b/)
# so we can swap implementations without touching the others.
#
# Usage:
#   .\\demovideo\\run.ps1                  # interactive menu
#   .\\demovideo\\run.ps1 -action create   # option 1: create demo video
#   .\\demovideo\\run.ps1 -action verify-a # option 2: structural review
#   .\\demovideo\\run.ps1 -action verify-b # option 3: vision-based review
#   .\\demovideo\\run.ps1 -action all      # run create then verify-a then verify-b

param([string]$action = '')

$ErrorActionPreference = 'Stop'
$here = Split-Path -Parent $MyInvocation.MyCommand.Path
$projectRoot = Split-Path -Parent $here

# Always git status first - never run without knowing the working tree state.
Push-Location $projectRoot
try {
    Write-Host '=== git status (pre-run check) ===' -ForegroundColor Cyan
    git status --short
    Write-Host '=============================' -ForegroundColor Cyan
    Write-Host ''
} finally { Pop-Location }

function Show-Menu {
    Write-Host 'Auditex Demo Video Pipeline' -ForegroundColor Yellow
    Write-Host '  1) create    - record demo video via playwright (Option 1)'
    Write-Host '  2) verify-a  - structural review: re-run with hard assertions (Option A)'
    Write-Host '  3) verify-b  - vision review: extract frames + OCR captions (Option B)'
    Write-Host '  4) all       - create, then verify-a, then verify-b'
    Write-Host '  q) quit'
    $choice = Read-Host 'Choose'
    return $choice
}

function Invoke-Action([string]$a) {
    switch ($a) {
        '1'       { & '$here\creation\run-creation.ps1' }
        'create' { & '$here\creation\run-creation.ps1' }
        '2'       { & '$here\verification-a\run-verify-a.ps1' }
        'verify-a' { & '$here\verification-a\run-verify-a.ps1' }
        '3'       { & '$here\verification-b\run-verify-b.ps1' }
        'verify-b' { & '$here\verification-b\run-verify-b.ps1' }
        '4' {
            & '$here\creation\run-creation.ps1'
            & '$here\verification-a\run-verify-a.ps1'
            & '$here\verification-b\run-verify-b.ps1'
        }
        'all' {
            & '$here\creation\run-creation.ps1'
            & '$here\verification-a\run-verify-a.ps1'
            & '$here\verification-b\run-verify-b.ps1'
        }
        default { Write-Host ('Unknown action: ' + $a) -ForegroundColor Red; exit 1 }
    }
}

if ([string]::IsNullOrWhiteSpace($action)) {
    $choice = Show-Menu
    if ($choice -eq 'q' -or $choice -eq 'Q') { exit 0 }
    Invoke-Action $choice
} else {
    Invoke-Action $action
}

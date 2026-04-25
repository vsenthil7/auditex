# Option B: Vision-based review - extract video frames + OCR captions against a rubric.
# Pipeline:
#   1. Pick most recent demo video from demo/
#   2. extract-frames.py: ffmpeg pulls 1 frame every 2 seconds
#   3. grade-frames.py: pytesseract OCRs each frame, checks against the rubric
#   4. JSON report saved to verification-b/reports/

$ErrorActionPreference = 'Stop'
$here = Split-Path -Parent $MyInvocation.MyCommand.Path
$projectRoot = Split-Path -Parent (Split-Path -Parent $here)
$demoDir = Join-Path $projectRoot 'demo'
$reportDir = Join-Path $here 'reports'
$framesDir = Join-Path $here 'frames'
New-Item -Path $reportDir -ItemType Directory -Force | Out-Null

Write-Host '' -ForegroundColor Yellow
Write-Host '[verify-b] === Vision-based review (Option B) === ' -ForegroundColor Yellow

# Find the latest video
$video = Get-ChildItem $demoDir -Filter '*.webm' -ErrorAction SilentlyContinue | Sort-Object LastWriteTime -Descending | Select-Object -First 1
if (-not $video) { Write-Host '[verify-b] no video found in demo/' -ForegroundColor Red; exit 1 }
Write-Host ('[verify-b] grading video: ' + $video.FullName)

# Pre-flight: ffmpeg and tesseract on PATH?
$ffmpegOk = (Get-Command ffmpeg -ErrorAction SilentlyContinue) -ne $null
$tesseractOk = (Get-Command tesseract -ErrorAction SilentlyContinue) -ne $null
if (-not $ffmpegOk) { Write-Host '[verify-b] ffmpeg NOT on PATH - install: winget install Gyan.FFmpeg' -ForegroundColor Yellow }
if (-not $tesseractOk) { Write-Host '[verify-b] tesseract NOT on PATH - install: winget install UB-Mannheim.TesseractOCR' -ForegroundColor Yellow }
if (-not ($ffmpegOk -and $tesseractOk)) { Write-Host '[verify-b] aborting - install missing deps and retry' -ForegroundColor Red; exit 2 }

$stamp = Get-Date -Format 'yyyyMMdd_HHmmss'
$thisFramesDir = Join-Path $framesDir $stamp
$reportFile = Join-Path $reportDir (('vision-review-' + $stamp + '.json'))

Write-Host '[verify-b] step 1: extract frames (1 per 2s)' -ForegroundColor Cyan
python (Join-Path $here 'extract-frames.py') --video $video.FullName --out $thisFramesDir --every 2.0
if ($LASTEXITCODE -ne 0) { Write-Host '[verify-b] extract failed' -ForegroundColor Red; exit 1 }

Write-Host '[verify-b] step 2: OCR + grade against rubric' -ForegroundColor Cyan
python (Join-Path $here 'grade-frames.py') --frames $thisFramesDir --report $reportFile
$gradeRc = $LASTEXITCODE

Write-Host '' -ForegroundColor Green
Write-Host ('[verify-b] report -> ' + $reportFile) -ForegroundColor Green
if ($gradeRc -ne 0) {
    Write-Host '[verify-b] some rubric items failed - see report; consider tuning end-to-end-demo.spec.ts and re-recording (Option 1).' -ForegroundColor Yellow
    Write-Host '[verify-b] auto-loop: not enabled by default. To enable, set $env:AUTO_LOOP=1 and re-run.' -ForegroundColor Yellow
}
exit $gradeRc

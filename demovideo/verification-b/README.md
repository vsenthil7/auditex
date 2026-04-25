# verification-b/ - Option B: Vision-based review

Genuinely watches the recorded video. Uses ffmpeg to extract still frames, then Tesseract OCR
to read the captions and UI text in each frame, and grades against a rubric.

## Modular pieces

- `extract-frames.py` - ffmpeg wrapper, pulls 1 frame every N seconds (default 2)
- `grade-frames.py` - OCR each frame with pytesseract, check against `RUBRIC` constant
- `run-verify-b.ps1` - wrapper: pre-flight + extract + grade + report
- `requirements.txt` - Python deps (pillow, pytesseract, opencv-headless)

## Prerequisites (one-time)

```powershell
winget install Gyan.FFmpeg
winget install UB-Mannheim.TesseractOCR
pip install -r demovideo/verification-b/requirements.txt
```

## Run
```powershell
.\demovideo\verification-b\run-verify-b.ps1
```

## Rubric

Each rubric entry passes if at least one extracted frame contains all the required substrings:

| Rubric item | Required substrings |
|---|---|
| title-card-intro | Auditex, EU AI ACT COMPLIANCE |
| caption-tc-1 | TC-DEMO-1, Contract Check, GIVEN, WHEN, THEN |
| caption-tc-2 | TC-DEMO-2, Risk Analysis, REJECT |
| caption-tc-3 | TC-DEMO-3, Document Review |
| pipeline-stages | Queued, Executing, Reviewing, Finalising, Completed |
| step-1-submission | STEP 1, SUBMISSION |
| step-2-executor | STEP 2, AI EXECUTOR |
| step-4-vertex | STEP 4, VERTEX CONSENSUS |

To extend, edit `RUBRIC` in `grade-frames.py`.

Output: `verification-b/reports/vision-review-{timestamp}.json` with per-rubric pass/fail.

# Option 3: Vision API tier (placeholder, not implemented)

When tesseract OCR fails on a frame (mean brightness <100, no text returned), escalate that frame to the Anthropic vision API to read it.

- Model: claude-sonnet-4-7 (multimodal)
- Cost: ~`$0.003/frame * ~10 caption frames = ~`$0.03/run
- Trigger: only frames that returned empty/garbage from tesseract
- Output: same JSON shape as grade-frames.py, written to demovideo/results/verification-b/

Implementation deferred. To enable: drop a `grade-via-vision-api.py` here + wire into run-verify-b.ps1 as a fallback step.

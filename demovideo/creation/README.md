# creation/ - Option 1: Record demo video

Coordinates the playwright spec at `frontend/tests/demo/end-to-end-demo.spec.ts` to record a captioned, narration-free walkthrough of the Auditex pipeline.

## What it does (5 steps)

1. Pre-flight checks (frontend + api containers up)
2. Bumps API rate limit to 600/min for the recording session
3. Runs the playwright spec with `DEMO=1` (slow-motion + visible cursor + captions)
4. Archives the video to `demo/end-to-end-{timestamp}.webm` and `demo/_backup/`
5. Reports the active video path

## Run
```powershell
.\demovideo\creation\run-creation.ps1
```

## Modular touch-points

- **Spec source:** `frontend/tests/demo/end-to-end-demo.spec.ts` (the recording flow itself).
- **Caption helper:** `frontend/tests/demo/caption-overlay.ts` (BDD scene cards).
- **Video archive:** `demo/` (active) + `demo/_backup/` (history).

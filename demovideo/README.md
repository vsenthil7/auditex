# Auditex Demo Video Pipeline

A modular pipeline for creating and reviewing the Auditex DoraHacks demo video.

Three independent options live in their own subfolders so we can swap implementations without touching the others.

## Folder layout

```
demovideo/
  run.ps1                wrapper - menu + dispatch
  README.md              this file
  creation/              Option 1 - record the demo video
  verification-a/        Option 2 - structural assertion review
  verification-b/        Option 3 - vision-based frame OCR review
```

## Usage

```powershell
.\demovideo\run.ps1                     # interactive menu
.\demovideo\run.ps1 -action create      # Option 1
.\demovideo\run.ps1 -action verify-a    # Option 2
.\demovideo\run.ps1 -action verify-b    # Option 3
.\demovideo\run.ps1 -action all         # 1 then 2 then 3
```

Every invocation prints `git status --short` first (project rule: git first, always).

## Prerequisites

- Docker Desktop running with the Auditex stack up (`docker compose up -d`).
- Frontend reachable on `http://localhost:3000`, API on `http://localhost:8000`.
- Option 3 additionally requires `ffmpeg` on PATH and Python 3.11+ with the deps in `verification-b/requirements.txt`.

## Outputs

- Recorded videos -> `demo/end-to-end-{timestamp}.webm` (kept locally, gitignored).
- Backup of every recording -> `demo/_backup/` (also gitignored).
- Verification reports -> `demovideo/verification-a/reports/` and `demovideo/verification-b/reports/`.

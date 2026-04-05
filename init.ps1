# P0-02: Git init for Auditex / PoC Engine
# Run once from the auditex directory:
#   cd C:\Users\v_sen\Documents\Projects\0001_Hack0014_Vertex_Swarm_Tashi\auditex
#   .\init.ps1

Set-Location $PSScriptRoot

Write-Host "=== P0-02: Git Init ===" -ForegroundColor Cyan
git init
git checkout -b main

Write-Host "`n=== Git status ===" -ForegroundColor Cyan
git status

Write-Host "`n=== Done. Paste output back to Claude. ===" -ForegroundColor Green

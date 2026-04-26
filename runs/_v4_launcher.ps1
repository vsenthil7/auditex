# Background launcher for HIL recording. Invoked by Claude to avoid shell timeout.
$ErrorActionPreference = 'Continue'
$root = 'C:\Users\v_sen\Documents\Projects\0001_Hack0014_Vertex_Swarm_Tashi\auditex'
Set-Location $root
& "$root\demovideo\creation\run-hil-video.ps1" *> "$root\runs\v4_recording_20260426.log"
"DONE_AT=$(Get-Date -Format 'yyyyMMdd_HHmmss')" | Out-File -Append -FilePath "$root\runs\v4_recording_20260426.log"

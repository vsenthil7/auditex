# run.ps1 -- Auditex universal run + log script
# Usage: powershell -ExecutionPolicy Bypass -File run.ps1 -cmd "docker compose ps"
# Multi-step: powershell -ExecutionPolicy Bypass -File run.ps1 -cmd "git add -A" -cmd2 "git status"
# Logs go to: runs\YYYYMMDD_HHMMSS_<slug>\run.log

param(
    [string]$cmd  = "docker compose ps",
    [string]$cmd2 = "",
    [string]$cmd3 = ""
)

$root   = $PSScriptRoot
$ts     = Get-Date -Format "yyyyMMdd_HHmmss"
$slug   = ($cmd -replace '[^a-zA-Z0-9]', '_')
$slug   = $slug.Substring(0, [Math]::Min(40, $slug.Length))
$runDir = Join-Path $root "runs\${ts}_${slug}"
New-Item -ItemType Directory -Force -Path $runDir | Out-Null
$log    = Join-Path $runDir "run.log"

function Write-Log($text, $color = "White") {
    Write-Host $text -ForegroundColor $color
    $text | Out-File $log -Encoding UTF8 -Append
}

# Header
Write-Log "================================================================================" "Cyan"
Write-Log "Auditex Run Log" "Cyan"
Write-Log "Date     : $(Get-Date -Format 'dd/MM/yyyy HH:mm:ss')" "Cyan"
Write-Log "Command  : $cmd" "Cyan"
Write-Log "Log      : $log" "Cyan"
Write-Log "================================================================================" "Cyan"

# Machine snapshot
Write-Log ""
Write-Log "--- MACHINE SNAPSHOT ---" "Yellow"
Write-Log "OS       : $([System.Environment]::OSVersion.VersionString)"
Write-Log "CPU      : $((Get-CimInstance Win32_Processor).Name)"
Write-Log "Cores    : $((Get-CimInstance Win32_Processor).NumberOfLogicalProcessors)"
Write-Log "RAM Total: $([Math]::Round((Get-CimInstance Win32_ComputerSystem).TotalPhysicalMemory/1GB,1)) GB"
Write-Log "RAM Free : $([Math]::Round((Get-Counter '\Memory\Available MBytes').CounterSamples[0].CookedValue/1024,1)) GB"
$drive = Get-PSDrive C
Write-Log "Disk C:  : Used: $([Math]::Round($drive.Used/1GB,1))GB  Free: $([Math]::Round($drive.Free/1GB,1))GB"
Write-Log "Docker   : $(docker --version 2>&1)"

# Docker stats
try {
    Write-Log ""
    Write-Log "--- DOCKER CONTAINER STATS ---" "Yellow"
    $stats = docker stats --no-stream --format "table {{.Name}}`t{{.CPUPerc}}`t{{.MemUsage}}`t{{.MemPerc}}" 2>&1
    Write-Log $stats
} catch {}

# Run commands
foreach ($c in @($cmd, $cmd2, $cmd3)) {
    if ([string]::IsNullOrWhiteSpace($c)) { continue }
    Write-Log ""
    Write-Log "--- RUNNING: $c ---" "Yellow"
    try {
        $out = Invoke-Expression $c 2>&1
        foreach ($line in $out) { Write-Log "$line" }
    } catch {
        Write-Log "ERROR: $_" "Red"
    }
}

Write-Log ""
Write-Log "--- END --- $(Get-Date -Format 'HH:mm:ss') ---" "Cyan"
Write-Log "Log: $log" "Green"

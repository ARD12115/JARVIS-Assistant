<#>
.SYNOPSIS
    JARVIS Assistant Emergency Stop - PowerShell Version
.DESCRIPTION
    Forcefully stops all JARVIS-related processes and cleans up traces.
    Run this if the launcher didn't clean up properly.
#>

$ErrorActionPreference = "SilentlyContinue"

Write-Host "==========================================" -ForegroundColor Cyan
Write-Host "   JARVIS Assistant Emergency Stop" -ForegroundColor Cyan
Write-Host "==========================================" -ForegroundColor Cyan
Write-Host ""

Write-Host "Killing processes on ports 8765 and 5173..." -ForegroundColor Yellow
$ports = @(8765, 5173)
foreach ($port in $ports) {
    $pids = netstat -ano | Select-String ":$port\s" | ForEach-Object {
        ($_ -split '\s+')[-1]
    } | Sort-Object -Unique
    foreach ($pid in $pids) {
        if ($pid -and $pid -ne "0") {
            Write-Host "  Killing PID $pid on port $port..." -ForegroundColor Gray
            Stop-Process -Id $pid -Force -ErrorAction SilentlyContinue
        }
    }
}

Write-Host "Killing JARVIS-named windows..." -ForegroundColor Yellow
$titles = @("JARVIS Python Backend*", "JARVIS Frontend*", "JARVIS Tauri App*")
foreach ($title in $titles) {
    $procs = Get-Process | Where-Object { $_.MainWindowTitle -like $title }
    foreach ($proc in $procs) {
        Write-Host "  Killing $($proc.ProcessName) (PID: $($proc.Id))..." -ForegroundColor Gray
        Stop-Process -Id $proc.Id -Force -ErrorAction SilentlyContinue
    }
}

Write-Host "Killing JARVIS project node/python processes..." -ForegroundColor Yellow
$jarvisProcs = Get-CimInstance Win32_Process | Where-Object {
    ($_.Name -eq "node.exe" -or $_.Name -eq "python.exe") -and
    ($_.CommandLine -like "*JARVIS*" -or $_.CommandLine -like "*jarvis*")
}
foreach ($proc in $jarvisProcs) {
    Write-Host "  Killing $($proc.Name) (PID: $($proc.ProcessId))..." -ForegroundColor Gray
    Stop-Process -Id $proc.ProcessId -Force -ErrorAction SilentlyContinue
}

Write-Host "Cleaning up PID files..." -ForegroundColor Yellow
Get-ChildItem "$env:TEMP\jarvis_pids_*.txt" -ErrorAction SilentlyContinue | Remove-Item -Force

Write-Host ""
Write-Host "All JARVIS processes stopped." -ForegroundColor Green
Write-Host "==========================================" -ForegroundColor Cyan

# Pause if run interactively
if ($Host.Name -eq "ConsoleHost" -and $MyInvocation.ExpectingInput) {
    Write-Host "Press any key to exit..." -ForegroundColor Gray
    $null = $Host.UI.RawUI.ReadKey("NoEcho,IncludeKeyDown")
}
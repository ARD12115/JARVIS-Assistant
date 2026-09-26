<#>
.SYNOPSIS
    JARVIS Assistant - Unified Launcher/Stopper
.DESCRIPTION
    Usage: launch_jarvis.ps1 [start|stop|restart|status]
    Starts Tauri native app which manages Python sidecar internally.
    Run from project root: C:\Projects\JARVIS-Assistant
#>

param(
    [string]$ProjectRoot = "C:\Projects\JARVIS-Assistant",
    [ValidateSet("start","stop","restart","status")]
    [string]$Action = "start"
)

$ErrorActionPreference = "Stop"

function Write-Header {
    Write-Host "==========================================" -ForegroundColor Cyan
    Write-Host "   JARVIS Assistant - Tauri Native App" -ForegroundColor Cyan
    Write-Host "==========================================" -ForegroundColor Cyan
    Write-Host "Project Root: $ProjectRoot" -ForegroundColor Yellow
    Write-Host "Action: $Action" -ForegroundColor Yellow
    Write-Host ""
}

function Cleanup-ExistingProcesses {
    Write-Host "Cleaning up any existing JARVIS processes..." -ForegroundColor Yellow
    
    # Kill by port
    $ports = @(8765, 5173)
    foreach ($port in $ports) {
        $processIds = netstat -ano | Select-String ":$port\s" | ForEach-Object {
            ($_ -split '\s+')[-1]
        } | Sort-Object -Unique
        foreach ($pid in $processIds) {
            if ($pid -and $pid -ne "0") {
                try { Stop-Process -Id $pid -Force -ErrorAction SilentlyContinue } catch {}
            }
        }
    }
    
    # Kill by window title
    $titles = @("JARVIS*")
    foreach ($title in $titles) {
        $processes = Get-Process | Where-Object { $_.MainWindowTitle -like $title }
        foreach ($proc in $processes) {
            try { Stop-Process -Id $proc.Id -Force -ErrorAction SilentlyContinue } catch {}
        }
    }
    
    # Kill by process name
    $processNames = @("jarvis-assistant", "python", "node")
    foreach ($name in $processNames) {
        $procs = Get-Process -Name $name -ErrorAction SilentlyContinue
        foreach ($proc in $procs) {
            if ($proc.MainWindowTitle -like "*JARVIS*" -or $proc.Path -like "*JARVIS*") {
                try { Stop-Process -Id $proc.Id -Force -ErrorAction SilentlyContinue } catch {}
            }
        }
    }
    
    Start-Sleep -Milliseconds 500
}

function Show-Status {
    Write-Host "Checking JARVIS processes..." -ForegroundColor Cyan
    Write-Host ""
    
    $ports = @(8765, 5173)
    foreach ($port in $ports) {
        $processIds = netstat -ano | Select-String ":$port\s" | ForEach-Object {
            ($_ -split '\s+')[-1]
        } | Sort-Object -Unique
        foreach ($pid in $processIds) {
            if ($pid -and $pid -ne "0") {
                Write-Host "Port $port: PID $pid RUNNING" -ForegroundColor Green
            }
        }
    }
    
    $processes = Get-Process -Name "jarvis-assistant", "python", "node" -ErrorAction SilentlyContinue
    if ($processes) {
        Write-Host ""
        Write-Host "Related Processes:" -ForegroundColor Cyan
        $processes | Select-Object Id, ProcessName, MainWindowTitle, CPU, WS | Format-Table -AutoSize
    }
}

# Main
Write-Header

$TauriDir = Join-Path $ProjectRoot "src-tauri"

# Validate directory
if (-not (Test-Path $TauriDir)) {
    Write-Error "Tauri directory not found: $TauriDir"
    exit 1
}

if (-not (Test-Path (Join-Path $ProjectRoot ".env"))) {
    Write-Warning ".env file not found. Copy .env.example to .env and configure API keys."
    Write-Host ""
}

switch ($Action) {
    "stop" {
        Write-Host "Stopping JARVIS Assistant..." -ForegroundColor Yellow
        Cleanup-ExistingProcesses
        Write-Host "All JARVIS processes stopped." -ForegroundColor Green
        break
    }
    "restart" {
        Write-Host "Restarting JARVIS Assistant..." -ForegroundColor Yellow
        Cleanup-ExistingProcesses
        Start-Sleep -Seconds 2
        # Fall through to start
    }
    "status" {
        Show-Status
        break
    }
    "start" {
        # Continue to start
    }
    default {
        Write-Error "Unknown action: $Action"
        exit 1
    }
}

if ($Action -ne "status" -and $Action -ne "stop") {
    # Start action
    if (-not (Test-Path (Join-Path $ProjectRoot ".env"))) {
        Write-Warning ".env file not found. Copy .env.example to .env and configure API keys."
        Write-Host ""
    }

    # Clean up any existing processes first
    Cleanup-ExistingProcesses

    Write-Host "Starting JARVIS Assistant (Tauri Native App)..." -ForegroundColor Green
    Write-Host ""

    # Check .env
    if (-not (Test-Path (Join-Path $ProjectRoot ".env"))) {
        Write-Warning ".env file not found. Copy .env.example to .env and configure API keys."
        Write-Host ""
    }

    # Start Tauri App - this manages Python sidecar internally
    Write-Host "[Tauri App] Starting..." -ForegroundColor Yellow
    Start-Process -FilePath "cmd.exe" -ArgumentList "/c", "cd /d `"$TauriDir`" && npx tauri dev" -WindowStyle Normal

    Write-Host ""
    Write-Host "==========================================" -ForegroundColor Cyan
    Write-Host "JARVIS Assistant started!" -ForegroundColor Green
    Write-Host "==========================================" -ForegroundColor Cyan
    Write-Host ""
    Write-Host "Native desktop window should open shortly." -ForegroundColor Cyan
    Write-Host "Close the window to stop the application." -ForegroundColor Cyan
    Write-Host ""
    Write-Host "Press any key to exit this launcher (app will keep running)..." -ForegroundColor Yellow
    $null = $Host.UI.RawUI.ReadKey("NoEcho,IncludeKeyDown")
}
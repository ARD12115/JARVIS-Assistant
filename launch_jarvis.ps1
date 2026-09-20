<#>
.SYNOPSIS
    JARVIS Assistant Launcher - PowerShell Version with Complete Cleanup
.DESCRIPTION
    Starts Python Backend, Frontend Dev Server, and Tauri App with proper process management
    and guaranteed cleanup on exit (Ctrl+C, error, or normal termination).
    Run from project root: C:\Projects\JARVIS-Assistant
#>

param(
    [string]$ProjectRoot = "C:\Projects\JARVIS-Assistant"
)

$ErrorActionPreference = "Stop"

# Global variable to track all child processes
$global:jarvisProcesses = @()
$global:pidFile = Join-Path $env:TEMP "jarvis_pids_$(Get-Random).txt"

function Write-Header {
    Write-Host "==========================================" -ForegroundColor Cyan
    Write-Host "   JARVIS Assistant Launcher (PowerShell)" -ForegroundColor Cyan
    Write-Host "==========================================" -ForegroundColor Cyan
    Write-Host "Project Root: $ProjectRoot" -ForegroundColor Yellow
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
    $titles = @("JARVIS Python Backend*", "JARVIS Frontend*", "JARVIS Tauri App*")
    foreach ($title in $titles) {
        $processes = Get-Process | Where-Object { $_.MainWindowTitle -like $title }
        foreach ($proc in $processes) {
            try { Stop-Process -Id $proc.Id -Force -ErrorAction SilentlyContinue } catch {}
        }
    }
    
    # Kill any leftover node/python processes from previous runs
    $staleProcesses = Get-Process | Where-Object {
        ($_.ProcessName -eq "node" -or $_.ProcessName -eq "python") -and
        ($_.Path -like "*JARVIS*" -or $_.Path -like "*jarvis*")
    }
    foreach ($proc in $staleProcesses) {
        try { Stop-Process -Id $proc.Id -Force -ErrorAction SilentlyContinue } catch {}
    }
    
    Start-Sleep -Milliseconds 500
}

function Start-Service {
    param(
        [string]$Name,
        [string]$WorkingDir,
        [string]$Command,
        [string[]]$Args
    )
    
    Write-Host "[$Name] Starting..." -ForegroundColor Yellow
    
    # Use cmd /c for commands that need shell resolution (like npm, npx)
    $needsShell = @("npm", "npx", "node") -contains (Split-Path $Command -Leaf)
    
    $startInfo = New-Object System.Diagnostics.ProcessStartInfo
    if ($needsShell) {
        $startInfo.FileName = "cmd.exe"
        $startInfo.Arguments = "/c " + ($Command + " " + ($Args -join " "))
        $startInfo.UseShellExecute = $false
    } else {
        $startInfo.FileName = $Command
        $startInfo.Arguments = ($Args -join " ")
        $startInfo.UseShellExecute = $false
    }
    $startInfo.WorkingDirectory = $WorkingDir
    $startInfo.CreateNoWindow = $true
    $startInfo.RedirectStandardOutput = $true
    $startInfo.RedirectStandardError = $true
    
    $process = New-Object System.Diagnostics.Process
    $process.StartInfo = $startInfo
    $process.EnableRaisingEvents = $true
    
    # Capture output for debugging
    $output = New-Object System.Text.StringBuilder
    $process.Add_OutputDataReceived({
        param($sender, $e)
        if ($e.Data) { $global:jarvisOutput.AppendLine("[$Name] $($e.Data)") }
    })
    $process.Add_ErrorDataReceived({
        param($sender, $e)
        if ($e.Data) { $global:jarvisError.AppendLine("[$Name] ERROR: $($e.Data)") }
    })
    
    $global:jarvisOutput = New-Object System.Text.StringBuilder
    $global:jarvisError = New-Object System.Text.StringBuilder
    
    if ($process.Start()) {
        $process.BeginOutputReadLine()
        $process.BeginErrorReadLine()
        $global:jarvisProcesses += @{
            Name = $Name
            Process = $process
            Id = $process.Id
        }
        "$Name=$($process.Id)" | Out-File -FilePath $global:pidFile -Append -Encoding utf8
        Write-Host "[$Name] Started (PID: $($process.Id))" -ForegroundColor Green
        return $process
    } else {
        Write-Error "Failed to start $Name"
        return $null
    }
}

function Stop-AllServices {
    Write-Host "`nShutting down all JARVIS services..." -ForegroundColor Yellow
    
    # Stop tracked processes
    foreach ($entry in $global:jarvisProcesses) {
        try {
            if (-not $entry.Process.HasExited) {
                $entry.Process.Kill()
                $entry.Process.WaitForExit(5000)
                Write-Host "[$($entry.Name)] Stopped (PID: $($entry.Id))" -ForegroundColor Green
            }
        } catch {
            Write-Warning "Failed to stop $($entry.Name): $_"
        }
    }
    
    # Fallback: kill by port
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
    
    # Fallback: kill by window title
    $titles = @("JARVIS Python Backend*", "JARVIS Frontend*", "JARVIS Tauri App*")
    foreach ($title in $titles) {
        $processes = Get-Process | Where-Object { $_.MainWindowTitle -like $title }
        foreach ($proc in $processes) {
            try { Stop-Process -Id $proc.Id -Force -ErrorAction SilentlyContinue } catch {}
        }
    }
    
    # Clean up PID file
    if (Test-Path $global:pidFile) {
        Remove-Item $global:pidFile -Force -ErrorAction SilentlyContinue
    }
    
    Write-Host "All services stopped." -ForegroundColor Green
}

# Setup cleanup on exit (Ctrl+C, error, normal exit)
function Invoke-Cleanup {
    Stop-AllServices
    exit 0
}

# Trap Ctrl+C only in interactive mode
if ([System.Console]::IsInputRedirected -eq $false) {
    try {
        [System.Console]::CancelKeyPress.Add({
            param($sender, $e)
            $e.Cancel = $true
            Invoke-Cleanup
        })
    } catch {
        # CancelKeyPress not available in non-interactive mode
    }
}

# Main
Write-Header

$PythonDir = Join-Path $ProjectRoot "src_python"
$FrontendDir = Join-Path $ProjectRoot "src-frontend"
$TauriDir = Join-Path $ProjectRoot "src-tauri"

# Validate directories
foreach ($dir in @($PythonDir, $FrontendDir, $TauriDir)) {
    if (-not (Test-Path $dir)) {
        Write-Error "Directory not found: $dir"
        exit 1
    }
}

if (-not (Test-Path (Join-Path $ProjectRoot ".env"))) {
    Write-Warning ".env file not found. Copy .env.example to .env and configure API keys."
    Write-Host ""
}

# Clean up any existing processes first
Cleanup-ExistingProcesses

Write-Host "Starting JARVIS Assistant services..." -ForegroundColor Green
Write-Host ""

# Clear PID file
New-Item -Path $global:pidFile -ItemType File -Force | Out-Null

# 1. Python Backend
$pythonProcess = Start-Service -Name "Python Backend" -WorkingDir $PythonDir `
    -Command "$PythonDir\.venv\Scripts\python.exe" -Args @("main.py")
$env:PYTHONPATH = "$ProjectRoot\src_python"
Start-Sleep -Seconds 3

# 2. Frontend Dev Server
$frontendProcess = Start-Service -Name "Frontend" -WorkingDir $FrontendDir `
    -Command "npm" -Args @("run", "dev")
Start-Sleep -Seconds 5

# 3. Tauri App
$tauriProcess = Start-Service -Name "Tauri App" -WorkingDir $TauriDir `
    -Command "npx" -Args @("tauri", "dev")

Write-Host ""
Write-Host "==========================================" -ForegroundColor Cyan
Write-Host "All services started!" -ForegroundColor Green
Write-Host "==========================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "Python Backend:  http://127.0.0.1:8765" -ForegroundColor Cyan
Write-Host "Frontend Dev:    http://localhost:5173" -ForegroundColor Cyan
Write-Host "Tauri App:       Native desktop window" -ForegroundColor Cyan
Write-Host ""
Write-Host "PID file: $global:pidFile" -ForegroundColor Gray
Write-Host "Press Ctrl+C to stop all services cleanly." -ForegroundColor Yellow
Write-Host ""

# Monitor processes and keep script alive
try {
    while ($true) {
        Start-Sleep -Seconds 5
        
        # Check for failed processes
        foreach ($entry in $global:jarvisProcesses) {
            if ($entry.Process.HasExited) {
                $exitCode = $entry.Process.ExitCode
                if ($exitCode -ne 0) {
                    Write-Error "[$($entry.Name)] Process exited with code $exitCode"
                    # Read captured error output
                    if ($global:jarvisError.Length -gt 0) {
                        Write-Host $global:jarvisError.ToString() -ForegroundColor Red
                    }
                }
            }
        }
    }
}
catch {
    Write-Error "Launcher error: $_"
}
finally {
    Invoke-Cleanup
}
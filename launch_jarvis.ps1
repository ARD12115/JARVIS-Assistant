<#>
.SYNOPSIS
    JARVIS Assistant Launcher - PowerShell Version
.DESCRIPTION
    Starts Python Backend, Frontend Dev Server, and Tauri App in separate windows.
    Run from project root: C:\Projects\JARVIS-Assistant
#>

param(
    [string]$ProjectRoot = "C:\Projects\JARVIS-Assistant"
)

$ErrorActionPreference = "Stop"

Write-Host "==========================================" -ForegroundColor Cyan
Write-Host "   JARVIS Assistant Launcher (PowerShell)" -ForegroundColor Cyan
Write-Host "==========================================" -ForegroundColor Cyan
Write-Host "Project Root: $ProjectRoot" -ForegroundColor Yellow
Write-Host ""

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

Write-Host "Starting JARVIS Assistant services..." -ForegroundColor Green
Write-Host ""

# Start Python Backend
Write-Host "[1/3] Starting Python Backend..." -ForegroundColor Yellow
$pythonJob = Start-Job -ScriptBlock {
    param($PythonDir, $ProjectRoot)
    Set-Location $PythonDir
    $env:PYTHONPATH = "$ProjectRoot\src_python"
    & ".venv\Scripts\python.exe" main.py
} -ArgumentList $PythonDir, $ProjectRoot

Start-Sleep -Seconds 3

# Start Frontend
Write-Host "[2/3] Starting Frontend Dev Server..." -ForegroundColor Yellow
$frontendJob = Start-Job -ScriptBlock {
    param($FrontendDir)
    Set-Location $FrontendDir
    npm run dev
} -ArgumentList $FrontendDir

Start-Sleep -Seconds 5

# Start Tauri
Write-Host "[3/3] Starting Tauri App..." -ForegroundColor Yellow
$tauriJob = Start-Job -ScriptBlock {
    param($TauriDir)
    Set-Location $TauriDir
    npx tauri dev
} -ArgumentList $TauriDir

Write-Host ""
Write-Host "==========================================" -ForegroundColor Cyan
Write-Host "All services started!" -ForegroundColor Green
Write-Host "==========================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "Python Backend:  http://127.0.0.1:8765" -ForegroundColor Cyan
Write-Host "Frontend Dev:    http://localhost:5173" -ForegroundColor Cyan
Write-Host "Tauri App:       Native desktop window" -ForegroundColor Cyan
Write-Host ""
Write-Host "Jobs running in background. Press Ctrl+C to stop all." -ForegroundColor Yellow
Write-Host ""

try {
    # Keep script running and show job status
    while ($true) {
        Start-Sleep -Seconds 10
        $jobs = Get-Job
        foreach ($job in $jobs) {
            if ($job.State -eq "Failed") {
                Write-Error "Job $($job.Name) failed: $($job.Error)"
                Receive-Job $job
            }
        }
    }
}
finally {
    Write-Host "`nShutting down services..." -ForegroundColor Yellow
    Get-Job | Stop-Job | Remove-Job
    Write-Host "All services stopped." -ForegroundColor Green
}
@echo off
REM JARVIS Assistant - Unified Launcher/Stopper
REM Usage: launch_jarvis.bat [start|stop|restart|status]
REM Run from project root: C:\Projects\JARVIS-Assistant

setlocal enabledelayedexpansion

set "PROJECT_ROOT=C:\Projects\JARVIS-Assistant"
set "TAURI_DIR=%PROJECT_ROOT%\src-tauri"
set "ACTION=%~1"
if "%ACTION%"=="" set "ACTION=start"

echo ==========================================
echo   JARVIS Assistant - Tauri Native App
echo ==========================================
echo Project Root: %PROJECT_ROOT%
echo Action: %ACTION%
echo.

REM Check directories
if not exist "%TAURI_DIR%" (
    echo ERROR: Tauri directory not found: %TAURI_DIR%
    pause
    exit /b 1
)

if "%ACTION%"=="stop" goto :stop
if "%ACTION%"=="status" goto :status
if "%ACTION%"=="restart" goto :restart

:start
echo Starting JARVIS Assistant (Tauri Native App)...
echo.

REM Check .env
if not exist "%PROJECT_ROOT%\.env" (
    echo WARNING: .env file not found. Copy .env.example to .env and configure API keys.
    echo.
)

REM Kill any existing JARVIS processes first
call :cleanup_existing

echo Starting JARVIS Assistant (Tauri Native App)...
echo.

REM Start Tauri App - this manages Python sidecar internally
start "JARVIS Assistant" cmd /k "
    cd /d %TAURI_DIR%
    npx tauri dev
"

echo.
echo ==========================================
echo JARVIS Assistant started!
echo ==========================================
echo.
echo Native desktop window should open shortly.
echo Close the window to stop the application.
echo.
echo Press any key to exit this launcher (app will keep running).
echo.
pause
goto :eof

:stop
echo Stopping JARVIS Assistant...
echo.
call :cleanup_existing
echo.
echo All JARVIS processes stopped.
echo ==========================================
pause
goto :eof

:restart
echo Restarting JARVIS Assistant...
echo.
call :cleanup_existing
echo.
timeout /t 2 >nul
goto :start

:status
echo Checking JARVIS processes...
echo.
for /f "tokens=5" %%p in ('netstat -ano ^| findstr ":8765 :5173"') do (
    if "%%p" NEQ "0" (
        echo Port %%p: PID %%p RUNNING
    )
)
tasklist /FI "IMAGENAME eq jarvis-assistant.exe" /FI "IMAGENAME eq python.exe" /FI "IMAGENAME eq node.exe" /FO TABLE
echo.
pause
goto :eof

:cleanup_existing
REM Kill any existing processes on our ports
for /f "tokens=5" %%p in ('netstat -ano ^| findstr ":8765 :5173"') do (
    if "%%p" NEQ "0" taskkill /F /PID %%p >nul 2>&1
)
REM Kill any existing JARVIS windows
taskkill /F /FI "WINDOWTITLE eq JARVIS*" >nul 2>&1
taskkill /F /FI "IMAGENAME eq jarvis-assistant.exe" >nul 2>&1
taskkill /F /FI "IMAGENAME eq python.exe" /FI "WINDOWTITLE eq JARVIS*" >nul 2>&1
taskkill /F /FI "IMAGENAME eq node.exe" /FI "WINDOWTITLE eq JARVIS*" >nul 2>&1
goto :eof
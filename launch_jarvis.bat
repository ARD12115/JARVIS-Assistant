@echo off
REM JARVIS Assistant Launcher - Windows Batch Version
REM Starts Python Backend, Frontend Dev Server, and Tauri App with proper cleanup
REM Run from project root: C:\Projects\JARVIS-Assistant

setlocal enabledelayedexpansion

set "PROJECT_ROOT=C:\Projects\JARVIS-Assistant"
set "PYTHON_DIR=%PROJECT_ROOT%\src_python"
set "FRONTEND_DIR=%PROJECT_ROOT%\src-frontend"
set "TAURI_DIR=%PROJECT_ROOT%\src-tauri"
set "PID_FILE=%TEMP%\jarvis_pids_%RANDOM%.txt"

echo ==========================================
echo   JARVIS Assistant Launcher
echo ==========================================
echo Project Root: %PROJECT_ROOT%
echo.

REM Check directories
if not exist "%PYTHON_DIR%" (
    echo ERROR: Python directory not found: %PYTHON_DIR%
    pause
    exit /b 1
)
if not exist "%FRONTEND_DIR%" (
    echo ERROR: Frontend directory not found: %FRONTEND_DIR%
    pause
    exit /b 1
)
if not exist "%TAURI_DIR%" (
    echo ERROR: Tauri directory not found: %TAURI_DIR%
    pause
    exit /b 1
)

REM Check .env
if not exist "%PROJECT_ROOT%\.env" (
    echo WARNING: .env file not found. Copy .env.example to .env and configure API keys.
    echo.
)

REM Kill any existing JARVIS processes first
call :cleanup_existing

echo Starting JARVIS Assistant services...
echo.

REM Clear PID file
type nul > "%PID_FILE%"

REM Start Python Backend
echo [1/3] Starting Python Backend...
start "JARVIS Python Backend" /B cmd /c "
    cd /d %PYTHON_DIR%
    set PYTHONPATH=%PROJECT_ROOT%\src_python
    .venv\Scripts\python.exe main.py
"
REM Get PID of the python process
for /f "tokens=2" %%i in ('tasklist /FI "IMAGENAME eq python.exe" /FI "WINDOWTITLE eq JARVIS Python Backend*" /FO CSV /NH 2^>nul') do (
    set PYTHON_PID=%%~i
    echo PYTHON=%%~i >> "%PID_FILE%"
)
timeout /t 3 >nul

REM Start Frontend Dev Server
echo [2/3] Starting Frontend Dev Server...
start "JARVIS Frontend" /B cmd /c "
    cd /d %FRONTEND_DIR%
    npm run dev
"
for /f "tokens=2" %%i in ('tasklist /FI "IMAGENAME eq node.exe" /FI "WINDOWTITLE eq JARVIS Frontend*" /FO CSV /NH 2^>nul') do (
    set FRONTEND_PID=%%~i
    echo FRONTEND=%%~i >> "%PID_FILE%"
)
timeout /t 5 >nul

REM Start Tauri App
echo [3/3] Starting Tauri App...
start "JARVIS Tauri App" /B cmd /c "
    cd /d %TAURI_DIR%
    npx tauri dev
"
for /f "tokens=2" %%i in ('tasklist /FI "IMAGENAME eq node.exe" /FI "WINDOWTITLE eq JARVIS Tauri App*" /FO CSV /NH 2^>nul') do (
    set TAURI_PID=%%~i
    echo TAURI=%%~i >> "%PID_FILE%"
)

echo.
echo ==========================================
echo All services started!
echo ==========================================
echo.
echo Python Backend:  http://127.0.0.1:8765
echo Frontend Dev:    http://localhost:5173
echo Tauri App:       Native desktop window
echo.
echo PID file: %PID_FILE%
echo Press Ctrl+C to stop all services cleanly.
echo.

REM Trap Ctrl+C for cleanup
set "CTRL_C_HANDLED=0"

:WAIT_LOOP
timeout /t 2 >nul
if not exist "%PID_FILE%" goto :CLEANUP_EXIT
goto :WAIT_LOOP

:CLEANUP_EXISTING
REM Kill any existing processes on our ports
for /f "tokens=5" %%p in ('netstat -ano ^| findstr ":8765 :5173"') do (
    taskkill /F /PID %%p >nul 2>&1
)
REM Kill any existing JARVIS windows
taskkill /F /FI "WINDOWTITLE eq JARVIS Python Backend*" >nul 2>&1
taskkill /F /FI "WINDOWTITLE eq JARVIS Frontend*" >nul 2>&1
taskkill /F /FI "WINDOWTITLE eq JARVIS Tauri App*" >nul 2>&1
goto :EOF

:CLEANUP
echo.
echo Shutting down services...
if exist "%PID_FILE%" (
    for /f "tokens=1,2 delims==" %%a in (%PID_FILE%) do (
        taskkill /F /PID %%b >nul 2>&1
        echo Stopped %%a (PID: %%b)
    )
    del "%PID_FILE%" 2>nul
)
REM Also kill by port as fallback
for /f "tokens=5" %%p in ('netstat -ano ^| findstr ":8765 :5173"') do (
    taskkill /F /PID %%p >nul 2>&1
)
taskkill /F /FI "WINDOWTITLE eq JARVIS Python Backend*" >nul 2>&1
taskkill /F /FI "WINDOWTITLE eq JARVIS Frontend*" >nul 2>&1
taskkill /F /FI "WINDOWTITLE eq JARVIS Tauri App*" >nul 2>&1
echo All services stopped.
goto :EOF

:CLEANUP_EXIT
call :CLEANUP
exit /b 0
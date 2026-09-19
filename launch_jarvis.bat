@echo off
REM JARVIS Assistant Launcher
REM Starts Python Backend, Frontend Dev Server, and Tauri App
REM Run this from the project root: C:\Projects\JARVIS-Assistant

set PROJECT_ROOT=C:\Projects\JARVIS-Assistant
set PYTHON_DIR=%PROJECT_ROOT%\src_python
set FRONTEND_DIR=%PROJECT_ROOT%\src-frontend
set TAURI_DIR=%PROJECT_ROOT%\src-tauri

echo ==========================================
echo   JARVIS Assistant Launcher
echo ==========================================
echo Project Root: %PROJECT_ROOT%
echo.

REM Check if directories exist
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

REM Check for .env file
if not exist "%PROJECT_ROOT%\.env" (
    echo WARNING: .env file not found. Copy .env.example to .env and configure API keys.
    echo.
)

echo Starting JARVIS Assistant services...
echo.

REM Start Python Backend in new window
echo [1/3] Starting Python Backend...
start "JARVIS Python Backend" cmd /k "
    cd /d %PYTHON_DIR%
    set PYTHONPATH=%PROJECT_ROOT%\src_python
    .venv\Scripts\python.exe main.py
"

REM Wait a moment for backend to start
timeout /t 3 >nul

REM Start Frontend Dev Server in new window
echo [2/3] Starting Frontend Dev Server...
start "JARVIS Frontend" cmd /k "
    cd /d %FRONTEND_DIR%
    npm run dev
"

REM Wait for frontend to compile
timeout /t 5 >nul

REM Start Tauri App in new window
echo [3/3] Starting Tauri App...
start "JARVIS Tauri App" cmd /k "
    cd /d %TAURI_DIR%
    npx tauri dev
"

echo.
echo ==========================================
echo All services started!
echo ==========================================
echo.
echo Python Backend:  http://127.0.0.1:8765
echo Frontend Dev:    http://localhost:5173
echo Tauri App:       Native desktop window
echo.
echo Close individual windows to stop services.
echo.
pause
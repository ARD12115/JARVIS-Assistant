@echo off
REM JARVIS Assistant Stop Script - Emergency Cleanup
REM Run this if the launcher didn't clean up properly

echo ==========================================
echo   JARVIS Assistant Emergency Stop
echo ==========================================
echo.

echo Killing processes on ports 8765 and 5173...
for /f "tokens=5" %%p in ('netstat -ano ^| findstr ":8765 :5173"') do (
    if "%%p" NEQ "0" (
        echo Killing PID %%p on port...
        taskkill /F /PID %%p >nul 2>&1
    )
)

echo Killing JARVIS-named windows...
taskkill /F /FI "WINDOWTITLE eq JARVIS Python Backend*" >nul 2>&1
taskkill /F /FI "WINDOWTITLE eq JARVIS Frontend*" >nul 2>&1
taskkill /F /FI "WINDOWTITLE eq JARVIS Tauri App*" >nul 2>&1

echo Killing any node/python processes in JARVIS project...
wmic process where "name='node.exe' and CommandLine like '%%JARVIS%%'" delete >nul 2>&1
wmic process where "name='python.exe' and CommandLine like '%%JARVIS%%'" delete >nul 2>&1

echo Cleaning up PID files...
del "%TEMP%\jarvis_pids_*.txt" 2>nul

echo.
echo All JARVIS processes stopped.
echo ==========================================
pause
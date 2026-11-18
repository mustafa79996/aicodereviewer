@echo off
title Stop AI Code Reviewer Server
setlocal enabledelayedexpansion

echo ======================================================================
echo    Stopping AI Code Reviewer Background Server
echo ======================================================================

set FOUND=0
for /f "tokens=5" %%a in ('netstat -aon ^| findstr ":8000" ^| findstr "LISTENING"') do (
    set PID=%%a
    if not "!PID!"=="" (
        echo Terminating process on port 8000 (PID: !PID!)...
        taskkill /F /PID !PID! >nul 2>&1
        set FOUND=1
    )
)

if "!FOUND!"=="1" (
    echo [SUCCESS] Server stopped successfully.
) else (
    echo [INFO] No server was running on port 8000.
)

pause

@echo off
title AI Code Reviewer Server Status
setlocal enabledelayedexpansion

echo ======================================================================
echo    Checking AI Code Reviewer Server Status
echo ======================================================================

set FOUND=0
for /f "tokens=5" %%a in ('netstat -aon ^| findstr ":8000" ^| findstr "LISTENING"') do (
    set PID=%%a
    if not "!PID!"=="" (
        echo [LIVE] AI Code Reviewer is actively RUNNING!
        echo Process ID (PID): !PID!
        echo Port:             8000
        echo Local URL:        http://localhost:8000
        echo Local IP URL:     http://127.0.0.1:8000
        set FOUND=1
    )
)

if "!FOUND!"=="0" (
    echo [OFFLINE] Server is currently NOT running.
    echo To start it live in background: run start_live.bat
    echo To start it in terminal:        run start.bat
)

echo.
pause

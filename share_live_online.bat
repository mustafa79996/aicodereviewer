@echo off
title Share AI Code Reviewer Live Online
cd /d "%~dp0"

echo ======================================================================
echo    Instant Live Online Sharing (Public URL)
echo ======================================================================
echo.
echo Make sure your local server is running (start.bat or start_live.bat).
echo This script will generate a FREE, public HTTPS URL you can share
echo with anyone on the internet so they can access your AI Code Reviewer!
echo.

where npx >nul 2>&1
if %ERRORLEVEL% EQU 0 (
    echo Starting public HTTPS tunnel via localtunnel...
    echo (If prompted, press Y to install)
    echo.
    npx -y localtunnel --port 8000
) else (
    echo [NOTE] Node.js/npx was not found.
    echo You can also use Cloudflare Tunnel:
    echo download cloudflared and run: cloudflared.exe tunnel --url http://localhost:8000
    echo Or deploy for free 24/7 on Render by following DEPLOYMENT.md!
    echo.
    pause
)

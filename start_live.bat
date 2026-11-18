@echo off
title AI Code Reviewer - Make Live 24/7
cd /d "%~dp0"

echo ======================================================================
echo    Starting AI Code Reviewer in the Background (Always Live 24/7)
echo ======================================================================

set PYTHONPATH=%~dp0
set PYTHONUTF8=1

set PYTHON_EXE=%~dp0venv\Scripts\python.exe
if not exist "%PYTHON_EXE%" (
    set PYTHON_EXE=python
)

:: Start minimized in the background so it never exits and stays live 24/7
start "AI Code Reviewer Server" /min "%PYTHON_EXE%" "%~dp0run_server.py" --host 0.0.0.0 --port 8000

echo Waiting for server to initialize...
timeout /t 2 /nobreak >nul

:: Open browser
start "" "http://localhost:8000"

echo.
echo [SUCCESS] Server is now running live in the background!
echo Web Dashboard: http://localhost:8000
echo Local IP URL:  http://127.0.0.1:8000
echo.
echo - To check server status: double-click status.bat
echo - To stop the server:    double-click stop_server.bat
echo - To make it autostart:  double-click install_autostart.bat
echo.
pause

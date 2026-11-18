@echo off
title AI Code Reviewer - Live Reload Mode
setlocal enabledelayedexpansion

chcp 65001 >nul
set PYTHONUTF8=1

cd /d "%~dp0"

echo ======================================================================
echo    Starting AI Code Reviewer with Live Auto-Reload (Port 8000)
echo ======================================================================

set PYTHONPATH=%~dp0

set PYTHON_EXE=%~dp0venv\Scripts\python.exe
if not exist "%PYTHON_EXE%" (
    set PYTHON_EXE=python
)

echo Any changes you save to Python/HTML/JS files will auto-reload immediately!
start "" "http://localhost:8000"
"%PYTHON_EXE%" "%~dp0run_server.py" --host 0.0.0.0 --port 8000 --reload

pause

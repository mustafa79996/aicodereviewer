@echo off
title AI Code Review and Bug Detection System
setlocal enabledelayedexpansion

chcp 65001 >nul
set PYTHONUTF8=1

cd /d "%~dp0"

echo ======================================================================
echo    Starting AI Code Review and Bug Detection System (Port 8000)
echo ======================================================================

set PYTHONPATH=%~dp0

:: Find python executable in venv or fallback to system python
set PYTHON_EXE=%~dp0venv\Scripts\python.exe
if not exist "%PYTHON_EXE%" (
    set PYTHON_EXE=python
)

echo Launching server and opening your web browser at http://localhost:8000 ...
start "" "http://localhost:8000"
"%PYTHON_EXE%" "%~dp0run_server.py" --host 0.0.0.0 --port 8000

pause

@echo off
title AI Code Review and Bug Detection System
cd /d D:\ai-code-reviewer

echo ======================================================================
echo    Starting AI Code Review and Bug Detection System (Port 8000)
echo ======================================================================

set PYTHONPATH=D:\ai-code-reviewer
D:\ai-code-reviewer\venv\Scripts\python.exe D:\ai-code-reviewer\run_server.py

pause

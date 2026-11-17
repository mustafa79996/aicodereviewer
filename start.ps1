# PowerShell Startup Script for AI Code Reviewer
$ErrorActionPreference = "Stop"

Set-Location -Path "D:\ai-code-reviewer"
Write-Host "======================================================================" -ForegroundColor Cyan
Write-Host "   Starting AI Code Review and Bug Detection System (Port 8000)" -ForegroundColor Green
Write-Host "======================================================================" -ForegroundColor Cyan

$env:PYTHONPATH = "D:\ai-code-reviewer"
& "D:\ai-code-reviewer\venv\Scripts\python.exe" "D:\ai-code-reviewer\run_server.py"

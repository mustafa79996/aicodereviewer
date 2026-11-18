# PowerShell Startup Script for AI Code Reviewer
$ErrorActionPreference = "Stop"

$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location -Path $ScriptDir

Write-Host "======================================================================" -ForegroundColor Cyan
Write-Host "   Starting AI Code Review and Bug Detection System (Port 8000)" -ForegroundColor Green
Write-Host "======================================================================" -ForegroundColor Cyan

$env:PYTHONPATH = $ScriptDir

$PythonExe = Join-Path $ScriptDir "venv\Scripts\python.exe"
if (-not (Test-Path $PythonExe)) {
    $PythonExe = "python"
}

Start-Process "http://localhost:8000"
& $PythonExe (Join-Path $ScriptDir "run_server.py") --host 0.0.0.0 --port 8000

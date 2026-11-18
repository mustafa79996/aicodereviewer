@echo off
title Install Auto-Start on Windows Boot
setlocal

echo ======================================================================
echo    Configuring AI Code Reviewer to Run Automatically on Boot
echo ======================================================================

powershell -ExecutionPolicy Bypass -Command "$ws = New-Object -ComObject WScript.Shell; $s = $ws.CreateShortcut([System.IO.Path]::Combine($env:APPDATA, 'Microsoft\Windows\Start Menu\Programs\Startup', 'AICodeReviewer.lnk')); $s.TargetPath = '%~dp0start_live.bat'; $s.WorkingDirectory = '%~dp0'; $s.WindowStyle = 7; $s.Description = 'AI Code Reviewer Background Service'; $s.Save(); Write-Host '[SUCCESS] Windows Startup shortcut created successfully!' -ForegroundColor Green"

echo.
echo [DONE] Every time your computer boots or restarts, AI Code Reviewer
echo will automatically launch in the background and stay live 24/7 at:
echo http://localhost:8000
echo.
echo To remove auto-start later, double-click: uninstall_autostart.bat
echo.
pause

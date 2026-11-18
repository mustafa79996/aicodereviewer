@echo off
title Uninstall Auto-Start
setlocal

echo ======================================================================
echo    Removing AI Code Reviewer Auto-Start Shortcut
echo ======================================================================

set SHORTCUT=%APPDATA%\Microsoft\Windows\Start Menu\Programs\Startup\AICodeReviewer.lnk
if exist "%SHORTCUT%" (
    del "%SHORTCUT%"
    echo [SUCCESS] Auto-start shortcut removed successfully.
) else (
    echo [INFO] No auto-start shortcut was found.
)

pause

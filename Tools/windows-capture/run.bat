@echo off
title NOOP Windows Collector
echo ===================================================
echo Starting NOOP Windows 11 WHOOP Collector...
echo Connecting to Home Lab at https://acer-homelab.tail614bb9.ts.net
echo ===================================================
echo.

:: pushd automatically maps a temporary drive letter if running from a UNC path (e.g. \\wsl.localhost)
pushd "%~dp0"

echo Installing / verifying Python dependencies...
python -m pip install -r requirements.txt
if %ERRORLEVEL% neq 0 (
    echo.
    echo [ERROR] Failed to install dependencies. Please ensure Python is installed and added to PATH.
    pause
    popd
    exit /b %ERRORLEVEL%
)

echo.
echo Starting NOOP Collector Agent...
echo (If this is your first connect, double-tap the WHOOP 4.0 until it pulses blue!)
echo.
python -m noop_agent.main
popd
pause

@echo off
title Bulk Video Editor & Remixer (Reels Optimizer)
cd /d "%~dp0"

where python >nul 2>nul
if %ERRORLEVEL% NEQ 0 (
    echo [ERROR] Python is not installed or not in PATH!
    pause
    exit /b 1
)

python gui.py
if %ERRORLEVEL% NEQ 0 (
    echo.
    echo Something went wrong while running the app.
    pause
)

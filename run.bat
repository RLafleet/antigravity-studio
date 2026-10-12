@echo off
title Antigravity Studio
cd /d "%~dp0"
echo Starting Antigravity Studio Desktop...
python main.py %*
if %ERRORLEVEL% NEQ 0 (
    echo.
    echo Application exited with code %ERRORLEVEL%.
    pause
)

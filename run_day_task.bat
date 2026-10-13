@echo off
title Antigravity Day Task Runner (Slow & Steady)
cd /d "%~dp0"
echo ========================================================
echo  🐢 Antigravity Slow ^& Steady Day Task Daemon
echo  Режим: Никакой спешки. Чекпоинты. Охлаждение квот.
echo ========================================================
echo.
python day_orchestrator.py %*
if %ERRORLEVEL% NEQ 0 (
    echo.
    echo Script exited with code %ERRORLEVEL%.
    pause
)

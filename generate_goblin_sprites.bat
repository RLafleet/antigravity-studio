@echo off
chcp 65001 >nul
title Google AI Studio (Nano Banana PRO) Sprite Bot
color 0A

echo ================================================================
echo  🍌 Google AI Studio (Nano Banana PRO) Sprite Generator
echo  Автономный бот для генерации и нарезки спрайтов гоблина
echo ================================================================
echo.

cd /d "%~dp0"
python -u tools/playwright_studio_bot.py

echo.
echo ================================================================
echo  Генерация и нарезка завершены! Нажмите любую клавишу для выхода.
echo ================================================================
pause >nul

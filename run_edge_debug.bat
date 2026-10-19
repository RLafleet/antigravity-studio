@echo off
echo ========================================================
echo  Запуск Microsoft Edge с портом отладки 9222
echo  Это позволит боту Antigravity Studio подключиться
echo  к вашему активному сеансу Google AI Studio PRO!
echo ========================================================
echo.
echo Закрытие фоновых процессов Edge (если есть)...
taskkill /F /IM msedge.exe >nul 2>&1
timeout /t 1 >nul
start "" "C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe" --remote-debugging-port=9222 --disable-backgrounding-occluded-windows --disable-renderer-backgrounding --disable-background-timer-throttling "https://aistudio.google.com/prompts/new_chat"
echo Edge запущен с защитой от засыпания! Теперь бот может автоматически генерировать спрайты даже когда Edge свернут.

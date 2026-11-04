@echo off
title EVAC-TWIN Launcher

echo ==========================================
echo          EVAC-TWIN COMMAND CENTER
echo ==========================================
echo.

echo Starting Mosquitto MQTT Broker...
start "EVAC-TWIN - MQTT" cmd /k "cd /d C:\Program Files\mosquitto && mosquitto.exe -v"

timeout /t 2 /nobreak >nul

echo Starting EVAC-TWIN Backend on port 8001...
start "EVAC-TWIN - Backend" cmd /k "cd /d C:\EVAC-TWIN\backend && .\.venv\Scripts\activate && python -m uvicorn app.main:app --reload --port 8001"

timeout /t 4 /nobreak >nul

echo Starting EVAC-TWIN Frontend...
start "EVAC-TWIN - Frontend" cmd /k "cd /d C:\EVAC-TWIN\frontend && npm run dev"

timeout /t 3 /nobreak >nul

echo Starting EVAC-TWIN IoT Simulator...
start "EVAC-TWIN - IoT Simulator" cmd /k "cd /d C:\EVAC-TWIN\backend && .\.venv\Scripts\activate && python -m app.iot_simulator"

echo.
echo ==========================================
echo       EVAC-TWIN SERVICES STARTED
echo ==========================================
echo.
echo MQTT     : localhost:1883
echo Backend  : http://localhost:8001
echo Frontend : http://localhost:5173
echo.
echo Opening dashboard...
timeout /t 8 /nobreak >nul

start http://localhost:5173

exit
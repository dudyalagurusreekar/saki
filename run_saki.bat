@echo off
title Saki AI Startup Manager
color 0B

echo ===================================================
echo               SAKI AI COMPANION STARTUP
echo ===================================================
echo.

:: 1. Check Virtual Environment
if exist venv goto HAS_VENV

echo [INFO] Virtual environment 'venv' not found. Creating venv...
if exist "C:\Users\gurus\AppData\Local\Programs\Python\Python312\python.exe" (
    "C:\Users\gurus\AppData\Local\Programs\Python\Python312\python.exe" -m venv venv
) else (
    python -m venv venv
)

echo [INFO] Installing Python dependencies...
venv\Scripts\python -m pip install --upgrade pip
venv\Scripts\python -m pip install -r requirements.txt

:HAS_VENV

:: 2. Check Frontend node_modules
if exist frontend\node_modules goto HAS_NODE_MODULES

echo [INFO] Node modules not found in frontend. Installing dependencies...
cmd /c "cd frontend && npm install"

:HAS_NODE_MODULES

echo [1/2] Starting Saki FastAPI Backend (Port 8000)...
start "Saki AI Backend" cmd /k "venv\Scripts\python -m uvicorn backend.main:app --host 0.0.0.0 --port 8000 --reload"

echo [2/2] Starting Saki Next.js Frontend (Port 3000)...
start "Saki AI Frontend" cmd /k "cd frontend && npm run dev"

timeout /t 3 /nobreak > nul

echo [INFO] Opening Saki AI in your web browser...
start http://localhost:3000

echo.
echo ===================================================
echo Saki AI is fully launched and running!
echo.
echo Backend URL:  http://localhost:8000
echo Frontend URL: http://localhost:3000
echo ===================================================
echo.
echo Press any key to close this manager window.
pause > nul

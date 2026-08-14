@echo off
title Saki AI Startup Manager
color 0B

echo ==========================================
echo       SAKI AI COMPANION STARTUP
echo ==========================================
echo.

:: Check virtual environment
if not exist venv (
    echo [ERROR] Virtual environment 'venv' not found in root.
    echo Please build it and install dependencies.
    pause
    exit /b
)

:: Check frontend node_modules
if not exist frontend\node_modules (
    echo [WARNING] Node modules not found in frontend.
    echo Attempting to install frontend dependencies...
    cmd /c "cd frontend && npm install"
)

echo [1/2] Starting Saki FastAPI Backend (Port 8000)...
start "Saki AI Backend" cmd /k "venv\Scripts\python -m uvicorn backend.main:app --host 127.0.0.1 --port 8000 --reload"

timeout /t 2 /nobreak > nul

echo [2/2] Starting Saki Next.js Frontend (Port 3000)...
start "Saki AI Frontend" cmd /k "cd frontend && npm run dev"

echo.
echo ==========================================
echo Saki AI is launching!
echo Backend logs are running in a separate window.
echo Frontend logs are running in a separate window.
echo.
echo Backend URL:  http://localhost:8000
echo Frontend URL: http://localhost:3000
echo ==========================================
echo.
echo Press any key to exit this manager.
pause > nul

@echo off
title CyberSentinel AI Launcher
color 0A
echo ============================================================
echo         CYBERSENTINEL AI - STARTING FULL PLATFORM
echo ============================================================
echo.

cd /d "%~dp0"

echo [1/3] Starting Backend Server (FastAPI on http://127.0.0.1:8000)...
start "CyberSentinel Backend (Port 8000)" cmd /k "cd /d %~dp0backend && venv312\Scripts\python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload"

echo [2/3] Starting Frontend Server (Next.js on http://localhost:3000)...
start "CyberSentinel Frontend (Port 3000)" cmd /k "cd /d %~dp0frontend && npm run dev"

echo [3/3] Waiting for servers to initialize...
timeout /t 5 /nobreak >nul

echo.
echo ============================================================
echo   Platform is running!
echo   Frontend : http://localhost:3000
echo   Backend  : http://127.0.0.1:8000/docs
echo.
echo   Login Credentials:
echo   Email    : admin@cybersentinel.com
echo   Password : Admin@12345678
echo ============================================================
echo.

start http://localhost:3000
echo Opening browser... You can keep this window open or close it.
pause


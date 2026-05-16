@echo off
chcp 65001 >nul
title Vehicle Sensor Test System

REM ============================================================
REM   Vehicle Environmental Sensor Automated Test System
REM   Description: Auto start backend, frontend and sensor simulator
REM ============================================================

set VENV_PATH=X:\Code Projects\pyven\.venv
set PROJECT_ROOT=%~dp0

echo.
echo ================================================
echo   MQTT-based Vehicle Sensor Test System
echo ================================================
echo   Project Dir: %PROJECT_ROOT%
echo   Virtual Env: %VENV_PATH%
echo ================================================
echo.

if not exist "%VENV_PATH%\Scripts\activate.bat" (
    echo [ERROR] Virtual environment not found: %VENV_PATH%
    echo Please check VENV_PATH configuration in start.bat
    pause
    exit /b 1
)

echo [1/3] Starting Backend Service (FastAPI) ...
start "Backend - FastAPI" cmd /k "call "%VENV_PATH%\Scripts\activate.bat" && cd /d "%PROJECT_ROOT%backend" && uvicorn main:app --reload --host 0.0.0.0 --port 8000"

timeout /t 3 /nobreak >nul

echo [2/3] Starting Sensor Simulator ...
start "Sensor Simulator" cmd /k "call "%VENV_PATH%\Scripts\activate.bat" && cd /d "%PROJECT_ROOT%backend" && python sensor_simulator.py"

timeout /t 2 /nobreak >nul

echo [3/3] Starting Frontend Service (Vite) ...
start "Frontend - Vite" cmd /k "cd /d "%PROJECT_ROOT%frontend" && npm run dev"

echo.
echo ================================================
echo   All services started successfully!
echo ================================================
echo.
echo   Backend API Docs: http://localhost:8000/docs
echo   Frontend URL: http://localhost:5173
echo.
echo   Close command windows to stop services.
echo ================================================
echo.

pause
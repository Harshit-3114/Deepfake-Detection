@echo off
title Deepfake Detection System
cd /d "%~dp0"

echo =============================================
echo  Deepfake Detection System - Startup Script
echo =============================================
echo.

:: Check Docker
where docker >nul 2>&1
if %errorlevel% neq 0 (
    echo [ERROR] Docker is not installed or not in PATH.
    echo        Please install Docker Desktop from https://www.docker.com/products/docker-desktop/
    pause
    exit /b 1
)

:: Check Node.js
where node >nul 2>&1
if %errorlevel% neq 0 (
    echo [ERROR] Node.js is not installed or not in PATH.
    echo        Please install Node.js from https://nodejs.org/
    pause
    exit /b 1
)

:: Check if Docker is running
docker info >nul 2>&1
if %errorlevel% neq 0 (
    echo [ERROR] Docker daemon is not running.
    echo        Please start Docker Desktop first.
    pause
    exit /b 1
)

echo [INFO] Docker and Node.js detected.
echo.

:: Start backend services
echo [STEP 1/4] Building and starting backend services with Docker Compose...
docker-compose up --build -d
if %errorlevel% neq 0 (
    echo [ERROR] Docker Compose failed to start services.
    pause
    exit /b 1
)
echo [OK] Backend services started.
echo.

:: Wait for services to be healthy
echo [STEP 2/4] Waiting for services to be ready...
echo        (This may take 30-60 seconds for model downloads...)
timeout /t 10 /nobreak >nul

:: Check orchestrator health
:health_check
echo        Checking orchestrator health...
curl -s http://localhost:8400/health >nul 2>&1
if %errorlevel% neq 0 (
    choice /c RN /t 5 /d R /m "        Not ready yet. Retrying in 5s (or press N to skip)..."
    if errorlevel 2 goto skip_health
    goto health_check
)
:skip_health
echo [OK] Orchestrator service appears to be running.
echo.

:: Install frontend dependencies
echo [STEP 3/4] Installing frontend dependencies...
cd frontend
call npm install 2>&1 | findstr /v "npm WARN"
if %errorlevel% neq 0 (
    echo [WARNING] npm install had warnings, continuing...
)
cd ..
echo [OK] Frontend dependencies installed.
echo.

:: Start frontend
echo [STEP 4/4] Starting frontend dev server...
echo.
start "Deepfake Frontend" cmd /c "cd /d "%~dp0frontend" && npm run dev"

echo =============================================
echo  System is starting up!
echo =============================================
echo.
echo  Backend Services:
echo    Orchestrator API: http://localhost:8400
echo    Text Detector:    http://localhost:8001
echo    Image Detector:   http://localhost:8002
echo    Audio Detector:   http://localhost:8003
echo    Video Detector:   http://localhost:8004
echo    Fusion Service:   http://localhost:8005
echo    MinIO Console:    http://localhost:9001
echo.
echo  Frontend:
echo    Web UI:           http://localhost:5173
echo.
echo  Quick Test:
echo    curl -X POST -F "file=@test.txt" http://localhost:8400/ingest
echo.
echo  To stop: docker-compose down
echo =============================================
echo.

:: Run a quick self-test
echo [INFO] Running quick self-test...
echo test content > "%TEMP%\df_test.txt"
curl -s -X POST -F "file=@%TEMP%\df_test.txt" http://localhost:8400/ingest >nul 2>&1
del "%TEMP%\df_test.txt" >nul 2>&1
if %errorlevel% equ 0 (
    echo [OK] Self-test passed. The system is functional.
) else (
    echo [WARNING] Self-test failed. The system may still be starting up.
    echo        Try: curl -X POST -F "file=@test.txt" http://localhost:8400/ingest
)

echo.
echo Press any key to open the Web UI in your browser...
pause >nul
start http://localhost:5173
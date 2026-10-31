@echo off
echo ========================================================
echo        Outbound - Production Deployment Script
echo ========================================================

where docker >nul 2>&1
if %ERRORLEVEL% EQU 0 (
    echo [INFO] Docker detected. Checking Docker Engine status...
    docker info >nul 2>&1
    if %ERRORLEVEL% EQU 0 (
        echo [INFO] Docker daemon is running. Starting containerized deployment...
        docker compose up --build -d
        if %ERRORLEVEL% EQU 0 (
            echo.
            echo ========================================================
            echo [SUCCESS] Outbound deployed successfully via Docker!
            echo  - Frontend: http://localhost:3000
            echo  - Backend API: http://localhost:8000
            echo  - API Docs: http://localhost:8000/docs
            echo ========================================================
            exit /b 0
        )
    )
)

echo [INFO] Docker daemon not available or not running.
echo [INFO] Falling back to unified single-server production deployment...

cd frontend
echo [1/2] Building production frontend assets...
call npm run build
if %ERRORLEVEL% NEQ 0 (
    echo [ERROR] Frontend build failed.
    exit /b %ERRORLEVEL%
)
cd ..

echo [2/2] Launching Outbound FastAPI unified production server...
set PYTHONPATH=backend
backend\venv\Scripts\python.exe -m uvicorn api.main:app --host 0.0.0.0 --port 8000

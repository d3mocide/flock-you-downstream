@echo off
REM FlockYou API - Start Script (Windows)
REM
REM Usage: start.bat [native|docker]
REM   native - Run directly with Python (recommended for serial access)
REM   docker - Run with Docker Compose

setlocal enabledelayedexpansion

set MODE=%1
if "%MODE%"=="" set MODE=native

echo ==============================================
echo   FlockYou API Server
echo ==============================================

if "%MODE%"=="docker" (
    echo Starting with Docker Compose...
    
    docker --version >nul 2>&1
    if errorlevel 1 (
        echo ERROR: Docker is not installed. Please install Docker Desktop first.
        exit /b 1
    )
    
    docker compose up -d --build
    
    echo.
    echo Server starting in background...
    echo View logs:  docker compose logs -f
    echo Stop:       docker compose down
    echo.
    echo NOTE: Serial port access may not work in Docker on Windows.
    echo       For serial devices, use: start.bat native
    echo.
    echo Dashboard:  http://localhost:5000
    echo API Health: http://localhost:5000/api/health
    
) else (
    echo Starting natively with Python...
    
    python --version >nul 2>&1
    if errorlevel 1 (
        echo ERROR: Python is not installed. Please install Python 3.11+.
        exit /b 1
    )
    
    cd /d "%~dp0backend"
    
    REM Create virtual environment if it doesn't exist
    if not exist "venv" (
        echo Creating virtual environment...
        python -m venv venv
    )
    
    REM Activate virtual environment
    call venv\Scripts\activate.bat
    
    REM Install dependencies
    echo Installing dependencies...
    pip install -q -r requirements.txt
    
    echo.
    echo Starting server...
    echo Dashboard:  http://localhost:5000
    echo API Health: http://localhost:5000/api/health
    echo Press Ctrl+C to stop
    echo.
    
    python run.py
)

endlocal

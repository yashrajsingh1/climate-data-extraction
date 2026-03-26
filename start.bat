@echo off
REM ============================================================
REM Climate Data Extraction System - One-Click Setup
REM Run this script to install and start the application
REM ============================================================

echo.
echo ============================================================
echo    CLIMATE DATA EXTRACTION SYSTEM - SETUP
echo ============================================================
echo.

REM Check Python
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [ERROR] Python is not installed!
    echo Please install Python 3.11+ from https://python.org
    pause
    exit /b 1
)

echo [OK] Python found
echo.

REM Create virtual environment if not exists
if not exist ".venv" (
    echo [SETUP] Creating virtual environment...
    python -m venv .venv
)

REM Activate virtual environment
echo [SETUP] Activating virtual environment...
call .venv\Scripts\activate.bat

REM Upgrade pip
echo [SETUP] Upgrading pip...
python -m pip install --upgrade pip --quiet

REM Install dependencies
echo [SETUP] Installing dependencies...
pip install -r requirements.txt --quiet

REM Create data directories
if not exist "data\reports" mkdir data\reports

echo.
echo ============================================================
echo    SETUP COMPLETE - Starting Application
echo ============================================================
echo.
echo    Open in browser: http://localhost:5000
echo.
echo    Press Ctrl+C to stop the server
echo ============================================================
echo.

REM Start the application
python app.py

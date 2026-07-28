@echo off
title ParkEase - Starting...
cd /d "%~dp0backend"

echo ============================================
echo    ParkEase - Parking ^& Fuel Station BD
echo    University Project
echo ============================================
echo.

REM make sure python is actually installed
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [ERROR] Python is not installed!
    echo Download from: https://www.python.org/downloads/
    echo Make sure to check "Add Python to PATH" during installation.
    pause
    exit /b
)

REM install everything we need
echo [1/4] Installing dependencies...
pip install -q fastapi uvicorn sqlalchemy python-multipart passlib bcrypt pydantic itsdangerous 2>&1
if %errorlevel% neq 0 (
    echo [ERROR] Failed to install dependencies. Try running as Administrator.
    pause
    exit /b
)
echo       Done!

REM seed the db if this is the first run
echo [2/4] Setting up database...
if not exist "..\parking.db" (
    python seed.py >nul 2>&1
    echo       Database created with sample data!
) else (
    echo       Database already exists.
)

REM fire up the server
echo [3/4] Starting server...
start "ParkEase Server" cmd /k "cd /d "%~dp0backend" && python -m uvicorn app:app --host 0.0.0.0 --port 8000"

REM give it a couple secs to boot
timeout /t 3 /nobreak >nul

REM open the browser so they can see it
echo [4/4] Opening browser...
start "" "http://localhost:8000"

echo.
echo ============================================
echo    ParkEase is running!
echo    Local:  http://localhost:8000
echo.
echo    Share your IP with teammates:
echo    (run "ipconfig" to find your IPv4 address)
echo    Example: http://192.168.x.x:8000
echo ============================================
echo.
echo Press any key to stop the server...
pause

REM kill the python process on exit
taskkill /f /im "python.exe" /t >nul 2>&1
echo Server stopped.

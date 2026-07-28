@echo off
cd /d "C:\Users\Administrator\Desktop\Fuel Station\backend"
start "ParkEase Server" cmd /k "python -m uvicorn app:app --host 0.0.0.0 --port 8000"
timeout /t 3 /nobreak >nul
start "" "http://localhost:8000"
echo.
echo ParkEase is running at http://localhost:8000
echo.
pause

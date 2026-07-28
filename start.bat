@echo off
cd /d "C:\Users\Administrator\Desktop\Fuel Station\backend"
start "ParkEase Server" cmd /k "python -m uvicorn app:app --host 0.0.0.0 --port 8000"
timeout /t 3 /nobreak >nul
start "ngrok Tunnel" cmd /k "C:\Users\Administrator\Downloads\Compressed\ngrok-v3-stable-windows-amd64\ngrok.exe http 8000"
echo.
echo ParkEase is starting...
echo Server: http://localhost:8000
echo Ngrok URL will appear in the ngrok window.
echo.
pause

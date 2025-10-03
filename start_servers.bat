@echo off
echo Starting DigiClinic Servers...
echo.

cd /d "%~dp0"

echo Starting Backend Server...
start "Backend Server" cmd /k "cd backend && python main.py"

timeout /t 3 /nobreak >nul

echo Starting Frontend Server...
start "Frontend Server" cmd /k "cd frontend && npm run dev"

echo.
echo Both servers are starting...
echo Backend will be available at: http://localhost:8000
echo Frontend will be available at: http://localhost:8080 or http://localhost:5173
echo.
echo Press any key to exit...
pause >nul

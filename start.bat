@echo off
echo ========================================
echo QueryViz - Starting Services
echo ========================================
echo.

echo [1/2] Starting Backend on port 8000...
echo.
start cmd /k "cd backend && uvicorn main:app --reload --port 8000"

timeout /t 3 /nobreak > nul

echo [2/2] Starting Frontend on port 3000...
echo.
start cmd /k "cd frontend && npm run dev"

echo.
echo ========================================
echo Services Starting...
echo ========================================
echo.
echo Backend:  http://localhost:8000
echo Frontend: http://localhost:3000
echo.
echo Press any key to exit this window...
pause > nul

@echo off
echo Starting Finance App...

:: Start Backend in a new window
echo Starting Backend (FastAPI)...
start "Backend - FastAPI" cmd /k "cd backend && python -m uvicorn main:app --reload --port 8000"

:: Start Frontend in a new window
echo Starting Frontend (Vite)...
start "Frontend - Vite" cmd /k "cd frontend && npm run dev"

echo.
echo Both servers are starting in separate windows.
echo - Backend: http://localhost:8000/docs
echo - Frontend: http://localhost:5173
echo.
pause

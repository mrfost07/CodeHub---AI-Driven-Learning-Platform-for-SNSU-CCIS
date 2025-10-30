@echo off
echo ========================================
echo   Starting CodeHub Platform
echo ========================================
echo.
echo This will start both Backend and Frontend servers
echo.
echo Backend: http://localhost:8000
echo Frontend: http://localhost:3000
echo.
pause

echo.
echo Starting Backend Server...
start "CodeHub Backend" cmd /k "cd codehub_backend && ..\\venv\\Scripts\\activate && python manage.py runserver"

timeout /t 5

echo Starting Frontend Server...
start "CodeHub Frontend" cmd /k "cd frontend && set TSC_COMPILE_ON_ERROR=true && npm start"

echo.
echo ========================================
echo   CodeHub is starting...
echo ========================================
echo.
echo Backend: http://localhost:8000
echo Frontend: http://localhost:3000
echo Admin: http://localhost:8000/admin
echo.
echo Two new windows have opened:
echo   1. Backend (Django)
echo   2. Frontend (React)
echo.
echo Keep both windows open while using CodeHub!
echo.
echo First time? Create an admin account:
echo   cd codehub_backend
echo   ..\\venv\\Scripts\\activate
echo   python manage.py createsuperuser
echo.
pause


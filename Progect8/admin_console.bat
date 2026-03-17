@echo off
chcp 65001 >nul
setlocal enabledelayedexpansion

:menu
cls
echo.
echo ====================================
echo     ADMIN CONSOLE
echo ====================================
echo.
echo 1. Clear database
echo 2. Create demo data
echo 3. Reset and start fresh
echo 4. View admin password
echo 5. Exit
echo.
set /p choice="Select option (1-5): "

if "%choice%"=="1" goto clear_db
if "%choice%"=="2" goto demo_data
if "%choice%"=="3" goto reset_fresh
if "%choice%"=="4" goto view_password
if "%choice%"=="5" exit /b 0
echo Invalid choice
timeout /t 2 >nul
goto menu

:clear_db
echo.
if exist "instance\data.db" (
    del "instance\data.db"
    echo Database cleared successfully!
) else (
    echo Database not found
)
pause
goto menu

:demo_data
echo.
echo Creating demo data...
call .venv\Scripts\activate.bat
set FLASK_APP=backend.app
python -c "from app import app, db; app.app_context().push(); db.create_all(); print('Demo data created')"
echo.
pause
goto menu

:reset_fresh
echo.
echo Performing full reset...
if exist "instance\data.db" (
    del "instance\data.db"
    echo Database deleted
)
if exist ".venv" (
    echo Removing virtual environment...
    rmdir /s /q .venv
)
echo.
echo Creating new environment...
python -m venv .venv
call .venv\Scripts\activate.bat
pip install -r requirements.txt >nul 2>&1
echo Done! Run start.bat to begin
pause
goto menu

:view_password
echo.
echo Admin password is generated on server startup.
echo Run start.bat and check console output.
echo.
echo Password location: admin_password.txt
if exist "admin_password.txt" (
    echo.
    echo Current password:
    type admin_password.txt
)
pause
goto menu


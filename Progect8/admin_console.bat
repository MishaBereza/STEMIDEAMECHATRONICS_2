@echo off
chcp 65001 >nul
setlocal enabledelayedexpansion

set "PY_CMD="
set "VENV_PY=.venv\Scripts\python.exe"

where py >nul 2>&1
if not errorlevel 1 (
    py -3.14 --version >nul 2>&1
    if not errorlevel 1 set "PY_CMD=py -3.14"
)

if not defined PY_CMD (
    where python >nul 2>&1
    if not errorlevel 1 (
        for /f "delims=" %%i in ('python -c "import sys; print(f'{sys.version_info[0]}.{sys.version_info[1]}')" 2^>nul') do set "PY_VER=%%i"
        if "!PY_VER!"=="3.14" set "PY_CMD=python"
    )
)

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
set FLASK_APP=backend.app
if exist "%VENV_PY%" (
    call "%VENV_PY%" -c "from backend.app import app; from backend.models import db; app.app_context().push(); db.create_all(); print('Demo data created')"
) else (
    echo Virtual environment not found. Run start.bat first.
)
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
if not defined PY_CMD (
    echo ERROR: Python 3.14 was not found.
    pause
    goto menu
)
call %PY_CMD% -m venv .venv
if exist "%VENV_PY%" (
    call "%VENV_PY%" -m pip install -r requirements.txt >nul 2>&1
)
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


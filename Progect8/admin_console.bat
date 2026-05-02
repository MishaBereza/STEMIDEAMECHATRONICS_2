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

set "KEY_FILE=admin_key.txt"
if not exist "%KEY_FILE%" (
    echo ERROR: Admin key validation failed.
    pause
    exit /b 1
)

set "PY_VALIDATE=%VENV_PY%"
if not exist "%PY_VALIDATE%" if defined PY_CMD set "PY_VALIDATE=%PY_CMD%"
if not defined PY_VALIDATE (
    echo ERROR: Python is required to validate admin access.
    pause
    exit /b 1
)

"%PY_VALIDATE%" -c "import pathlib,hashlib,sys; data=pathlib.Path('admin_key.txt').read_text('utf-8').strip(); sys.exit(0 if hashlib.sha256(data.encode('utf-8')).hexdigest()=='a4b0ea41f07d266574fd953951872f69728da5fe3987d916ddc6322ce5ff585d' else 1)" >nul 2>&1
if errorlevel 1 (
    echo ERROR: Admin key validation failed.
    pause
    exit /b 1
)

:menu
echo.
echo ====================================
echo     ADMIN CONSOLE
echo ====================================
echo.
echo 1. Clear database and recreate over-admin
echo 2. Create demo data
echo 3. Reset and start fresh
echo 4. Switch this device to super-admin
echo 5. Ensure super-admin exists
echo 6. List jury/admin users
echo 7. Set user status
echo 8. Emergency stop server
echo 9. Change user password
echo 10. Toggle over admin enabled/disabled
echo 11. Exit
echo.
set /p choice="Select option (1-11): "

if "%choice%"=="1" goto clear_db
if "%choice%"=="2" goto demo_data
if "%choice%"=="3" goto reset_fresh
if "%choice%"=="4" goto switch_super_admin
if "%choice%"=="5" goto ensure_over_admin
if "%choice%"=="6" goto list_users
if "%choice%"=="7" goto set_status
if "%choice%"=="8" goto emergency_stop
if "%choice%"=="9" goto change_user_password
if "%choice%"=="10" goto toggle_over_admin
if "%choice%"=="11" exit /b 0
echo Invalid choice
timeout /t 2 >nul
goto menu

:clear_db
echo.
echo WARNING: This will delete all users, admins, teams, tournaments, rounds, submissions and settings.
echo The protected over-admin account will be recreated automatically.
set /p confirm_clear="Type DELETE to continue: "
if /i not "%confirm_clear%"=="DELETE" (
    echo Cancelled.
) else if exist "%VENV_PY%" (
    call "%VENV_PY%" scripts\admin_tools.py clear-database
) else (
    echo Virtual environment not found. Run start.bat first.
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

:switch_super_admin
echo.
if exist "%VENV_PY%" (
    call "%VENV_PY%" scripts\admin_tools.py ensure-over-admin
    echo Opening browser and switching this device to super-admin...
    start "" "http://localhost:5000/admin"
) else (
    echo Virtual environment not found. Run start.bat first.
)
echo.
pause
goto menu

:ensure_over_admin
echo.
if exist "%VENV_PY%" (
    call "%VENV_PY%" scripts\admin_tools.py ensure-over-admin
) else (
    echo Virtual environment not found. Run start.bat first.
)
echo.
pause
goto menu

:change_password
echo.
set /p new_password="Enter new admin password: "
if exist "%VENV_PY%" (
    call "%VENV_PY%" -c "from backend.app import app; from backend.auth import save_admin_password; app.app_context().push(); save_admin_password('%new_password%'); print('Admin password changed successfully!')"
) else (
    echo Virtual environment not found. Run start.bat first.
)
echo.
pause
goto menu

:list_users
echo.
echo Users with jury or admin status:
echo.
if exist "%VENV_PY%" (
    call "%VENV_PY%" scripts\admin_tools.py list-admins
) else (
    echo Virtual environment not found. Run start.bat first.
)
echo.
pause
goto menu

:set_status
echo.
set /p user_email="Enter user email: "
set /p new_status="Enter new status (0-participant, 1-jury, 3-admin): "
if "%new_status%"=="0" set "status_text=team"
if "%new_status%"=="1" set "status_text=jury"
if "%new_status%"=="3" set "status_text=admin"
if exist "%VENV_PY%" (
    call "%VENV_PY%" -c "from backend.app import app, db; from backend.models import User; from backend.auth import is_over_admin; app.app_context().push(); user = User.query.filter_by(email='%user_email%').first(); blocked = bool(user and is_over_admin(user)); print('User not found' if not user else ('Super-admin is protected' if blocked else f'User {user.first_name} {user.last_name} status updated to %status_text%')); user and not blocked and (setattr(user, 'role', '%status_text%'), db.session.commit())" 2>nul
) else (
    echo Virtual environment not found. Run start.bat first.
)
echo.
pause
goto menu

:emergency_stop
echo.
echo Emergency stop: shutting down run.py server...
if exist "%VENV_PY%" (
    powershell -NoLogo -NoProfile -Command "try { $p=Get-CimInstance Win32_Process | Where-Object { $_.CommandLine -match 'run\.py' }; if ($p) { $p | ForEach-Object { Stop-Process -Id $_.ProcessId -Force }; Write-Output 'Server stopped.' } else { Write-Output 'Server process not found.' } } catch { Write-Output 'Failed to stop server.'; exit 1 }"
) else (
    echo Virtual environment not found. Run start.bat first.
)
echo.
pause
goto menu

:change_user_password
echo.
set /p target_email="Enter user email: "
set /p new_user_password="Enter new password for user: "
if exist "%VENV_PY%" (
    call "%VENV_PY%" -c "from backend.app import app, db; from backend.models import User; from backend.auth import is_over_admin; app.app_context().push(); user = User.query.filter_by(email='%target_email%').first(); blocked = bool(user and is_over_admin(user)); print('User not found' if not user else ('Super-admin has no editable password' if blocked else 'User password changed successfully')); user and not blocked and user.set_password('%new_user_password%'); user and not blocked and db.session.commit()"
) else (
    echo Virtual environment not found. Run start.bat first.
)
echo.
pause
goto menu

:toggle_over_admin
echo.
echo Toggling over admin status...
if exist "%VENV_PY%" (
    call "%VENV_PY%" scripts\admin_tools.py toggle-over-admin
) else (
    echo Virtual environment not found. Run start.bat first.
)
echo.
pause
goto menu


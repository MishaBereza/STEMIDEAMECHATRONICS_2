@echo off
chcp 65001 >nul
setlocal

set "PY_CMD="
set "PY_VER=unknown"
set "VENV_PY=.venv\Scripts\python.exe"
set "RECREATE_VENV="

where py >nul 2>&1
if not errorlevel 1 (
    py -3.14 --version >nul 2>&1
    if not errorlevel 1 (
        set "PY_CMD=py -3.14"
        set "PY_VER=3.14"
    )
)

if not defined PY_CMD (
    where python >nul 2>&1
    if not errorlevel 1 (
        for /f "delims=" %%i in ('python -c "import sys; print(f'{sys.version_info[0]}.{sys.version_info[1]}')" 2^>nul') do set "PY_VER=%%i"
        if "!PY_VER!"=="3.14" (
            set "PY_CMD=python"
        )
    )
)

echo ====================================
echo Adaptive Tournament System
echo ====================================

if not defined PY_CMD (
    echo ERROR: Python 3.14 was not found.
    echo Install Python 3.14.3 and make sure the Python launcher is available.
    echo Recommended install: https://www.python.org/downloads/release/python-3143/
    pause
    exit /b 1
)

echo Using interpreter: %PY_CMD%

if exist "%VENV_PY%" (
    "%VENV_PY%" -c "import sys; sys.exit(0 if sys.version_info[:2] == (3, 14) else 1)" >nul 2>&1
    if errorlevel 1 (
        echo Existing virtual environment is missing or not Python 3.14. Recreating it...
        rmdir /s /q .venv
        set "RECREATE_VENV=1"
    )
)

if not exist ".venv" set "RECREATE_VENV=1"

if defined RECREATE_VENV (
    echo Creating virtual environment with Python 3.14...
    call %PY_CMD% -m venv .venv
    if errorlevel 1 (
        echo ERROR: Failed to create virtual environment.
        pause
        exit /b 1
    )
)

if not exist "%VENV_PY%" (
    echo ERROR: Virtual environment Python was not created.
    pause
    exit /b 1
)

if not exist "requirements.txt" (
    echo ERROR: requirements.txt not found.
    pause
    exit /b 1
)

echo Installing dependencies...
call "%VENV_PY%" -m pip install --upgrade pip
if errorlevel 1 (
    echo ERROR: Failed to upgrade pip inside the virtual environment.
    pause
    exit /b 1
)

call "%VENV_PY%" -m pip install -r requirements.txt
if errorlevel 1 (
    echo ERROR: Failed to install dependencies.
    pause
    exit /b 1
)

if not exist "run.py" (
    echo ERROR: run.py not found.
    pause
    exit /b 1
)

echo.
echo ====================================
echo Starting Flask Application
echo ====================================
echo.
echo Server: http://127.0.0.1:5000
echo Press Ctrl+C to stop the server.
echo.

call "%VENV_PY%" run.py

@echo off
chcp 65001 >nul
setlocal EnableDelayedExpansion

set "PY_CMD="
set "PY_VER=unknown"
set "VENV_PY=.venv\Scripts\python.exe"
set "RECREATE_VENV="

REM ====================================
REM Detect Python 3.14
REM ====================================

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
        for /f "delims=" %%i in ('python -c "import sys; print(f'{sys.version_info[0]}.{sys.version_info[1]}')" 2^>nul') do (
            set "PY_VER=%%i"
        )

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
    echo.
    echo Install Python 3.14.3:
    echo https://www.python.org/downloads/release/python-3143/
    echo.
    pause
    exit /b 1
)

echo Using interpreter: %PY_CMD%
echo Python version: %PY_VER%
echo.

REM ====================================
REM Check existing venv
REM ====================================

if exist "%VENV_PY%" (
    "%VENV_PY%" -c "import sys; sys.exit(0 if sys.version_info[:2] == (3,14) else 1)" >nul 2>&1

    if errorlevel 1 (
        echo Existing virtual environment is invalid or not Python 3.14
        echo Recreating virtual environment...
        rmdir /s /q .venv
        set "RECREATE_VENV=1"
    )
)

if not exist ".venv" (
    set "RECREATE_VENV=1"
)

REM ====================================
REM Create venv
REM ====================================

if defined RECREATE_VENV (
    echo Creating virtual environment...
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

REM ====================================
REM Restore pip
REM ====================================

echo Restoring pip...
call "%VENV_PY%" -m ensurepip --upgrade >nul 2>&1

REM ====================================
REM Check requirements
REM ====================================

if not exist "requirements.txt" (
    echo ERROR: requirements.txt not found.
    pause
    exit /b 1
)

REM ====================================
REM Upgrade pip
REM ====================================

echo Upgrading pip...
call "%VENV_PY%" -m pip install --upgrade pip

if errorlevel 1 (
    echo ERROR: Failed to upgrade pip inside the virtual environment.
    pause
    exit /b 1
)

REM ====================================
REM Install dependencies
REM ====================================

echo Installing dependencies...
call "%VENV_PY%" -m pip install -r requirements.txt

if errorlevel 1 (
    echo ERROR: Failed to install dependencies.
    pause
    exit /b 1
)

REM ====================================
REM Verify export libraries
REM ====================================

echo.
echo Verifying export libraries...

call "%VENV_PY%" -c "import reportlab; import openpyxl; print('OK')" >nul 2>&1

if errorlevel 1 (
    echo Installing missing export libraries...

    call "%VENV_PY%" -m pip install reportlab openpyxl

    if errorlevel 1 (
        echo ERROR: Failed to install export libraries.
        pause
        exit /b 1
    )
)

REM ====================================
REM Check Flask app
REM ====================================

if not exist "run.py" (
    echo ERROR: run.py not found.
    pause
    exit /b 1
)

REM ====================================
REM Start app
REM ====================================

echo.
echo ====================================
echo Starting Flask Application
echo ====================================
echo.
echo Server: http://127.0.0.1:5000
echo Press Ctrl+C to stop the server.
echo.

call "%VENV_PY%" run.py

pause
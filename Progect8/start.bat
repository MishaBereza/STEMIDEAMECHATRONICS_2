@echo off
setlocal enabledelayedexpansion

echo ====================================
echo Adaptive Tournament System
echo ====================================

REM Проверяем наличие Python
python --version >nul 2>&1
if errorlevel 1 (
    echo ERROR: Python не установлен
    pause
    exit /b 1
)

REM Создаем виртуальное окружение если его нет
if not exist ".venv" (
    echo Creating virtual environment...
    python -m venv .venv
)

call .venv\Scripts\activate.bat

if not exist "requirements.txt" (
    echo ERROR: requirements.txt не найден!
    pause
    exit /b 1
)

echo Installing dependencies...
pip install -r requirements.txt >nul 2>&1

if not exist "run.py" (
    echo ERROR: run.py не найден!
    pause
    exit /b 1
)

echo.
echo ====================================
echo Starting Flask Application
echo ====================================
echo.
echo Server: http://127.0.0.1:5000
echo.

python run.py




# Adaptive Tournament System Launcher (PowerShell)

Write-Host "====================================" -ForegroundColor Cyan
Write-Host "Adaptive Tournament System Launcher" -ForegroundColor Cyan
Write-Host "====================================" -ForegroundColor Cyan
Write-Host ""

# Проверяем наличие Python
try {
    python --version | Out-Null
} catch {
    Write-Host "ERROR: Python не установлен или не в PATH" -ForegroundColor Red
    Read-Host "Press Enter to exit"
    exit 1
}

# Создаем виртуальное окружение если его нет
if (-not (Test-Path ".venv")) {
    Write-Host ""
    Write-Host "Creating virtual environment..." -ForegroundColor Yellow
    python -m venv .venv
    Write-Host "Virtual environment created!" -ForegroundColor Green
}

# Активируем виртуальное окружение
Write-Host ""
Write-Host "Activating virtual environment..." -ForegroundColor Yellow
& .\.venv\Scripts\Activate.ps1

# Проверяем наличие requirements.txt
if (-not (Test-Path "requirements.txt")) {
    Write-Host "ERROR: requirements.txt не найден!" -ForegroundColor Red
    Read-Host "Press Enter to exit"
    exit 1
}

# Устанавливаем зависимости
Write-Host ""
Write-Host "Installing dependencies..." -ForegroundColor Yellow
pip install -r requirements.txt

# Проверяем наличие run.py
if (-not (Test-Path "run.py")) {
    Write-Host "ERROR: run.py не найден!" -ForegroundColor Red
    Read-Host "Press Enter to exit"
    exit 1
}

# Запускаем Flask приложение
Write-Host ""
Write-Host "====================================" -ForegroundColor Cyan
Write-Host "Starting Flask application..." -ForegroundColor Cyan
Write-Host "====================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "Сервер будет доступен по адресу:" -ForegroundColor Green
Write-Host "http://127.0.0.1:5000" -ForegroundColor Green
Write-Host ""
Write-Host "Нажмите CTRL+C для остановки сервера" -ForegroundColor Yellow
Write-Host ""

try {
    python run.py
} catch {
    Write-Host "Сервер закрыт" -ForegroundColor Yellow
}

Write-Host ""
Write-Host "====================================" -ForegroundColor Cyan
Write-Host "Сервер остановлен" -ForegroundColor Cyan
Write-Host "====================================" -ForegroundColor Cyan
Write-Host ""
Read-Host "Нажмите Enter для выхода"


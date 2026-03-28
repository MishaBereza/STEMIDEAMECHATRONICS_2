$ErrorActionPreference = "Stop"

Write-Host "====================================" -ForegroundColor Cyan
Write-Host "Adaptive Tournament System Launcher" -ForegroundColor Cyan
Write-Host "====================================" -ForegroundColor Cyan
Write-Host ""

$pythonCommand = $null
$pythonDisplay = $null

if (Get-Command py -ErrorAction SilentlyContinue) {
    try {
        & py -3.14 --version | Out-Null
        $pythonCommand = @("py", "-3.14")
        $pythonDisplay = "py -3.14"
    } catch {
    }
}

if (-not $pythonCommand -and (Get-Command python -ErrorAction SilentlyContinue)) {
    try {
        $detectedVersion = & python -c "import sys; print(f'{sys.version_info[0]}.{sys.version_info[1]}')"
        if ($detectedVersion -eq "3.14") {
            $pythonCommand = @("python")
            $pythonDisplay = "python"
        }
    } catch {
    }
}

if (-not $pythonCommand) {
    Write-Host "ERROR: Python 3.14 was not found." -ForegroundColor Red
    Write-Host "Install Python 3.14.3 and make sure the Python launcher is available." -ForegroundColor Red
    Write-Host "Recommended install: https://www.python.org/downloads/release/python-3143/" -ForegroundColor Red
    Read-Host "Press Enter to exit"
    exit 1
}

Write-Host "Using interpreter: $pythonDisplay" -ForegroundColor Green

$venvDir = Join-Path $PSScriptRoot ".venv"
$venvPython = Join-Path $venvDir "Scripts\python.exe"
$recreateVenv = $false

if (Test-Path $venvPython) {
    try {
        & $venvPython -c "import sys; sys.exit(0 if sys.version_info[:2] == (3, 14) else 1)" | Out-Null
    } catch {
        $recreateVenv = $true
    }

    if ($LASTEXITCODE -ne 0) {
        $recreateVenv = $true
    }
}

if (-not (Test-Path $venvDir)) {
    $recreateVenv = $true
}

if ($recreateVenv -and (Test-Path $venvDir)) {
    Write-Host "Existing virtual environment is missing or not Python 3.14. Recreating it..." -ForegroundColor Yellow
    Remove-Item -LiteralPath $venvDir -Recurse -Force
}

if ($recreateVenv) {
    Write-Host ""
    Write-Host "Creating virtual environment with Python 3.14..." -ForegroundColor Yellow
    if ($pythonCommand.Length -eq 1) {
        & $pythonCommand[0] -m venv .venv
    } else {
        & $pythonCommand[0] $pythonCommand[1] -m venv .venv
    }
    Write-Host "Virtual environment created." -ForegroundColor Green
}

if (-not (Test-Path $venvPython)) {
    Write-Host "ERROR: Virtual environment Python was not created." -ForegroundColor Red
    Read-Host "Press Enter to exit"
    exit 1
}

if (-not (Test-Path "requirements.txt")) {
    Write-Host "ERROR: requirements.txt not found." -ForegroundColor Red
    Read-Host "Press Enter to exit"
    exit 1
}

Write-Host ""
Write-Host "Installing dependencies..." -ForegroundColor Yellow
& $venvPython -m pip install --upgrade pip
& $venvPython -m pip install -r requirements.txt

if (-not (Test-Path "run.py")) {
    Write-Host "ERROR: run.py not found." -ForegroundColor Red
    Read-Host "Press Enter to exit"
    exit 1
}

Write-Host ""
Write-Host "====================================" -ForegroundColor Cyan
Write-Host "Starting Flask application..." -ForegroundColor Cyan
Write-Host "====================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "Server: http://127.0.0.1:5000" -ForegroundColor Green
Write-Host "Press Ctrl+C to stop the server." -ForegroundColor Yellow
Write-Host ""

try {
    & $venvPython run.py
} catch {
    Write-Host "Server stopped." -ForegroundColor Yellow
}

Write-Host ""
Write-Host "====================================" -ForegroundColor Cyan
Write-Host "Server stopped" -ForegroundColor Cyan
Write-Host "====================================" -ForegroundColor Cyan
Write-Host ""
Read-Host "Press Enter to exit"

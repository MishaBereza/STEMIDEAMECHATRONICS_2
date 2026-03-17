# Запускові скрипти

## admin_console.bat
- Запуск адміністративної консолі (необов'язковий, залежить від локальних налаштувань).
- Може викликати app.py або відкрити адресу /admin.

## start.bat
- Швидкий запуск сервера для Windows.
- Типово робить:
  - `set FLASK_APP=app.py`
  - `set FLASK_ENV=development`
  - `flask run`

## start.ps1
- PowerShell-варіант запуску:
  - ` $env:FLASK_APP = 'app.py'`
  - ` $env:FLASK_ENV = 'development'`
  - `flask run`

## Як користуватися
Відкриваєте PowerShell у корені проєкту та виконуєте:
```powershell
./start.ps1
``` або
```powershell
./start.bat
```
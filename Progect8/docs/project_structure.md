# project_structure_ukr.txt (документована версія)

## Призначення
Опис структури каталогу і ролі кожного файлу/папки у проекті.

## Структура
- `app.py` — основний сервер Flask і маршрутна логіка.
- `models.py` — ORM-моделі SQLAlchemy.
- `utils.py` — helper-функції (adaptive difficulty).
- `translations.py` — i18n словники та `get_text`.
- `demo_setup.py` — генерація початкових демо-даних.
- `admin_password.txt` — файл пароля адміна (при першому запуску створюється автоматично).
- `README.md` — швидкий старт.
- `requirements.txt` — залежності.
- `start.bat`/`start.ps1` - скрипти запуску.
- `templates/` — HTML-шаблони.
- `tests/` — pytest-онвери.
- `instance/`, `__pycache__/` — кеш/локальний стан.

## Як читати
Цей файл служить довідником по представленню надання новому розробнику чи рев'юеру.
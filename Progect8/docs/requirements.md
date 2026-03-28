# requirements.txt

## Призначення
Перелік Python-залежностей проєкту.

## Вміст
- Flask>=3.1,<3.2
- Flask-SQLAlchemy>=3.1,<3.2
- SQLAlchemy>=2.0.36,<2.1
- pytest>=8.3,<9
- python-dotenv>=1.0,<2

## Запуск
```powershell
pip install -r requirements.txt
```

## Рекомендація
При масштабуванні варто зафіксувати версію Python (напр. 3.11) та додати `pip-tools` / `poetry` для керування lock-файлом.

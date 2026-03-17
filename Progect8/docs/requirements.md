# requirements.txt

## Призначення
Перелік Python-залежностей проєкту.

## Вміст
- Flask==2.2.5
- Flask-SQLAlchemy==3.0.3
- SQLAlchemy==2.0.20
- pytest==7.4.0
- python-dotenv==1.0.0

## Запуск
```powershell
pip install -r requirements.txt
```

## Рекомендація
При масштабуванні варто зафіксувати версію Python (напр. 3.11) та додати `pip-tools` / `poetry` для керування lock-файлом.
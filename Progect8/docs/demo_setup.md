# demo_setup.py

## Призначення
Генерує демо-дані в БД:
- користувачі: admin/jury/captain/member
- турнір: `Demo Cup`
- раунд: `Round 1`
- команда: `Demo Team` з капітаном та учасником

## Особливості
- Метод виконується в `app.app_context()`
- Використовує `db.create_all()`
- Має дрібну помилку: імпорт `Team` відсутній, але створюється `Team` у коді (треба додати `from models import Team`)

## Виконання
`python demo_setup.py`

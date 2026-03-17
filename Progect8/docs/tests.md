# tests/

## Призначення
Покриття pytest для верифікації бізнес-логіки і моделей.

## Файли:
- `test_models.py` — тести моделей (`User`, `Tournament`, `Team`, `Round`, `Submission`, `Evaluation`) та зв'язків.
- `test_registration.py` — тестує /register та /tournament/<tid>/register, перевірку дублікатів.
- `test_team_submission.py` — на правильність submit/командна перевірка авторизації.
- `test_round_submission.py` — перевірка доступності по статусу турніру (Submission/Running).
- `test_admin_submission.py` — адмінські сторінки і дії з поданнями.
- `test_utils.py` — `calculate_average_score`, `adjust_difficulty`, `generate_new_round`.
- `test_deletion.py`, `test_admin_delete_user_team.py` — видалення користувачів/команд та консистентність БД.

## Запуск тестів
```powershell
python -m pytest
```

## Примітка
Якщо падає `detached instance` — перевірити, що всі об'єкти ORM використовуються в контексті сесії/додатка.
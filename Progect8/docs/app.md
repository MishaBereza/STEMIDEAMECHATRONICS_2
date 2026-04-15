# app.py

## Призначення
Основний Flask додаток і маршрути. Відповідає за логіку UI, сесії, CRUD-операції з турнірами, командами, поданнями та адміністрацію.

## Ключові компоненти

### Ініціалізація
- Flask app
- SQLAlchemy setup (`db.init_app(app)`)
- `SQLALCHEMY_DATABASE_URI` -> `sqlite:///data.db`
- `SECRET_KEY` з ENV або `dev-secret`

### Адмін пароль
- Зберігається в базі даних у таблиці `Settings` з ключем `admin_password`
- `get_or_create_admin_password()` -> читає з БД або створює запис з `admin123`
- `save_admin_password(new_password)` -> оновлює запис у БД

### Перевірка прав
- `admin_required` декоратор (перевірка `session['admin']`)
- `get_current_user()` -> з `session['user_id']`

### Контекстні процесори
- `inject_user` -> `get_current_user` доступний у шаблонах
- `translation` -> `t(key)`, `lang`, `supported_languages`

### Мовлення
- `/set_language/<lang>`: збереження у сесії (EN/UA)

### Маршрути користувача
- `/`: список турнірів
- `/register` GET/POST: реєстрація користувача (уникати дублікатів email / имени)
- `/tournament/<int:tid>`: деталі турніру + команда поточного користувача
- `/tournament/<int:tid>/register` GET/POST: реєстрація команди (captain + members)
- `/round/<int:rid>/submit` GET/POST: подати рішення по раунду (перевірка доступності статусу)
- `/team/<int:teamid>` GET/POST: редагування даних команди, відправка
- `/leaderboard/<int:tid>`: сформувати рейтинг команд по середньому балу
- `/user/<int:uid>`: профіль користувача, перелік турнірів

### Адмін маршрути
- `/admin` GET/POST: вхід
- `/admin/logout`
- `/admin/dashboard`
- `/admin/change_password` GET/POST
- `/admin/users`: список користувачів
- `/admin/user/<int:uid>/delete`: видалення користувача (захист admin / captain)
- `/admin/tournaments` + create/edit/delete
- `/admin/tournament/<int:tid>/teams`: команди турніру
- `/admin/team/<int:teamid>/delete`: очищення і видалення команди, submissions, evaluations
- `/admin/team/<int:teamid>/decide`: accept/reject/return

## Деталі бізнес-логіки
- Статуси турніру: Draft, Submission, Running, Finished
- `/round/<rid>/submit`: доступно коли статус tournament submission or running
- `team.submission_status` обробка Pending/Submitted/Accepted/Rejected/Returned
- при `Finished` у `team_page` auto mark `Submitted` для неподач

## Валідації
- `register_user`: унікальність email, first+last
- `register_team`: captain повинен існувати, нема дублікатів в рамках турніру
- `submit_solution`: обов'язковий `repo_url`; команда має належати до поточного турніру
- `team_page` edit: captain може змінювати список members

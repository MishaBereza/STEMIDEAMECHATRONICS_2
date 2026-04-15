Adaptive Difficulty Tournament System

Quick start

Recommended runtime: Python 3.13+

1. Create a virtual environment (recommended) and install dependencies:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

2. Run the app:

```powershell
set FLASK_APP=app.py
set FLASK_ENV=development
flask run
```

3. Open http://127.0.0.1:5000

Project structure

- `app.py` - Flask application and routes (including user/team registration, admin console, scoring and management)
- `models.py` - SQLAlchemy models (users, tournaments, teams, rounds, submissions, evaluations)
- `utils.py` - adaptive difficulty functions and helpers
- `templates/` - HTML templates with multi-language support (English/Ukrainian) and modern UI
- `tests/` - pytest unit tests for core logic

Additional features:

- Admin panel with password stored in database (default: 'admin123') available at `/admin`.
  - Manage users, tournaments, teams and submissions directly from browser.
  - Review submissions: accept/reject with comments.
  - Edit tournament metadata (name, description, max teams) and delete tournaments.
  - Disband teams, change team captains, and view team member lists.
- Language toggle (English / Ukrainian) in the navigation bar.
- Team management page allowing captains (verified by email) to edit member list and roles.
- Demo data creation route (`/create_demo_data`) for quick testing.
- Modern responsive design with gradient backgrounds and card-based layout.

Notes

This is a minimal, extendable scaffold implementing core features and the adaptive difficulty mechanism. You can expand authentication, authorization, UI and add more tests.

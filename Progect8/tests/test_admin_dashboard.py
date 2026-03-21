import os, sys
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from backend.app import app
from flask import render_template


def test_admin_dashboard_contains_create_link():
    # render the template directly to avoid test_client version issue
    with app.app_context():
        with app.test_request_context('/'):
            html = render_template(
                'admin_dashboard.html',
                users_count=1,
                tournaments_count=2,
                teams_count=3,
                submissions_count=4
            )
    assert '/admin/tournaments/create' in html
    assert 'Create Tournament' in html or 'Створити Турнір' in html  # english or ukr

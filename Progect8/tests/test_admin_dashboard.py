import os, sys
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from flask import render_template

from backend.app import app
from backend.models import User


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
    assert 'Create Tournament' in html or 'Створити Турнір' in html


def test_admin_route_auto_logs_in_over_admin():
    client = app.test_client()

    response = client.get('/admin', follow_redirects=False)

    assert response.status_code == 302
    assert response.headers['Location'].endswith('/admin/dashboard')

    with app.app_context():
        over_admin = User.query.filter_by(email='__super_admin__', role='admin').first()
        assert over_admin is not None

    with client.session_transaction() as sess:
        assert sess['admin'] is True
        assert sess['admin_user_id'] == over_admin.id

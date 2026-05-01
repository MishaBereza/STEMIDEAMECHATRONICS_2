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


def test_admin_route_requires_password_before_over_admin_login():
    client = app.test_client()

    response = client.get('/admin', follow_redirects=False)

    assert response.status_code == 200
    assert b'name="password"' in response.data

    with client.session_transaction() as sess:
        assert 'admin' not in sess
        assert 'admin_user_id' not in sess


def test_admin_route_logs_in_over_admin_with_password():
    from backend.auth import load_admin_password

    client = app.test_client()
    with app.app_context():
        password = load_admin_password()

    response = client.post('/admin', data={'password': password}, follow_redirects=False)

    assert response.status_code == 302
    assert response.headers['Location'].endswith('/admin/dashboard')

    with client.session_transaction() as sess:
        assert sess['admin'] is True
        admin_user_id = sess['admin_user_id']

    with app.app_context():
        over_admin = User.query.filter_by(email='over.admin@local', role='admin').first()
        assert over_admin is not None
        assert admin_user_id == over_admin.id

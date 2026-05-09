import os, sys
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from flask import render_template

from backend.app import app, db
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
    assert b'name="email"' in response.data
    assert b'name="password"' in response.data

    with client.session_transaction() as sess:
        assert 'admin' not in sess
        assert 'admin_user_id' not in sess


def test_admin_route_logs_in_regular_admin_with_email_and_password():
    with app.app_context():
        admin = User(first_name='Admin', last_name='User', email='admin@test.com', role='admin', is_verified=True)
        admin.set_password('secret123')
        db.session.add(admin)
        db.session.commit()
        admin_id = admin.id

    client = app.test_client()
    response = client.post('/admin', data={'email': 'admin@test.com', 'password': 'secret123'}, follow_redirects=False)

    assert response.status_code == 302
    assert response.headers['Location'].endswith('/admin/dashboard')

    with client.session_transaction() as sess:
        assert sess['admin'] is True
        assert sess['admin_user_id'] == admin_id
        assert sess['user_id'] == admin_id


def test_admin_route_does_not_auto_escalate_logged_in_admin_to_over_admin():
    with app.app_context():
        admin = User(first_name='Admin', last_name='User', email='admin2@test.com', role='admin', is_verified=True)
        admin.set_password('secret123')
        db.session.add(admin)
        db.session.commit()
        admin_id = admin.id

    client = app.test_client()
    with client.session_transaction() as sess:
        sess['user_id'] = admin_id

    response = client.get('/admin', follow_redirects=False)

    assert response.status_code == 200
    assert b'name="email"' in response.data

    with client.session_transaction() as sess:
        assert sess['user_id'] == admin_id
        assert 'admin' not in sess
        assert 'admin_user_id' not in sess


def test_logged_in_over_admin_can_open_admin_panel_without_reentering_password():
    from backend.auth import ensure_over_admin_user

    with app.app_context():
        over_admin = ensure_over_admin_user()
        over_admin_id = over_admin.id

    client = app.test_client()
    with client.session_transaction() as sess:
        sess['user_id'] = over_admin_id

    response = client.get('/admin', follow_redirects=False)

    assert response.status_code == 302
    assert response.headers['Location'].endswith('/admin/dashboard')

    with client.session_transaction() as sess:
        assert sess['user_id'] == over_admin_id
        assert sess['admin'] is True
        assert sess['admin_user_id'] == over_admin_id

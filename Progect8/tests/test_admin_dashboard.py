import os, sys
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from flask import render_template

from backend.app import app, db
from backend.models import User, Settings


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


def test_admin_route_logs_in_regular_admin_with_shared_admin_panel_password():
    with app.app_context():
        User.query.filter_by(email='admin@test.com').delete()
        admin = User(first_name='Admin', last_name='User', email='admin@test.com', role='admin', is_verified=True)
        Settings.query.filter_by(key='admin_password').delete()
        db.session.add(admin)
        db.session.add(Settings(key='admin_password', value='panel-secret'))
        db.session.commit()
        admin_id = admin.id

    client = app.test_client()
    response = client.post('/admin', data={'email': 'admin@test.com', 'password': 'panel-secret'}, follow_redirects=False)

    assert response.status_code == 302
    assert response.headers['Location'].endswith('/admin/dashboard')

    with client.session_transaction() as sess:
        assert sess['admin'] is True
        assert sess['admin_user_id'] == admin_id
        assert sess['user_id'] == admin_id


def test_admin_route_does_not_auto_escalate_logged_in_admin_to_over_admin():
    with app.app_context():
        User.query.filter_by(email='admin2@test.com').delete()
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


def test_over_admin_changes_admin_panel_password_without_changing_account_password():
    from backend.auth import ensure_over_admin_user, _load_admin_key_value

    with app.app_context():
        over_admin = ensure_over_admin_user()
        over_admin_id = over_admin.id
        original_password = _load_admin_key_value()
        Settings.query.filter_by(key='admin_password').delete()
        db.session.add(Settings(key='admin_password', value='admin123'))
        db.session.commit()

    client = app.test_client()
    with client.session_transaction() as sess:
        sess['user_id'] = over_admin_id
        sess['admin'] = True
        sess['admin_user_id'] = over_admin_id

    response = client.post(
        '/admin/change_password',
        data={'new_password': 'new-secret-123', 'confirm_password': 'new-secret-123'},
        follow_redirects=False,
    )

    assert response.status_code == 302
    assert response.headers['Location'].endswith('/admin/dashboard')

    with app.app_context():
        same_user = db.session.get(User, over_admin_id)
        admin_password = Settings.query.filter_by(key='admin_password').first()
        assert admin_password.value == 'new-secret-123'
        assert same_user.check_password(original_password)
        assert not same_user.check_password('new-secret-123')


def test_regular_admin_uses_updated_admin_panel_password_without_changing_account_password():
    with app.app_context():
        User.query.filter_by(email='panel-admin@test.com').delete()
        admin = User(first_name='Panel', last_name='Admin', email='panel-admin@test.com', role='admin', is_verified=True)
        admin.set_password('user-secret-123')
        Settings.query.filter_by(key='admin_password').delete()
        db.session.add(admin)
        db.session.add(Settings(key='admin_password', value='old-panel-secret'))
        db.session.commit()
        admin_id = admin.id

    client = app.test_client()
    with client.session_transaction() as sess:
        sess['user_id'] = admin_id
        sess['admin'] = True
        sess['admin_user_id'] = admin_id

    response = client.post(
        '/admin/change_password',
        data={'new_password': 'new-panel-secret', 'confirm_password': 'new-panel-secret'},
        follow_redirects=False,
    )

    assert response.status_code == 302
    assert response.headers['Location'].endswith('/admin/dashboard')

    fresh_client = app.test_client()
    login_response = fresh_client.post(
        '/admin',
        data={'email': 'panel-admin@test.com', 'password': 'new-panel-secret'},
        follow_redirects=False,
    )
    assert login_response.status_code == 302
    assert login_response.headers['Location'].endswith('/admin/dashboard')

    with app.app_context():
        same_user = User.query.filter_by(email='panel-admin@test.com').first()
        assert same_user.check_password('user-secret-123')
        assert not same_user.check_password('new-panel-secret')

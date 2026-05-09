import os
import sys

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from backend.app import app, db
from backend.models import User


def setup_function(function):
    with app.app_context():
        db.drop_all()
        db.create_all()


def test_existing_user_can_login_by_email():
    with app.app_context():
        user = User(first_name='Test', last_name='User', email='login@test.com', role='team')
        user.set_password('secret123')
        db.session.add(user)
        db.session.commit()
        user_id = user.id

    client = app.test_client()
    response = client.post('/login', data={'email': 'login@test.com', 'password': 'secret123'}, follow_redirects=False)

    assert response.status_code == 302
    assert response.headers['Location'].endswith(f'/user/{user_id}')

    with client.session_transaction() as sess:
        assert sess['user_id'] == user_id


def test_login_shows_error_for_missing_user():
    client = app.test_client()
    response = client.post('/login', data={'email': 'missing@test.com', 'password': 'secret123'}, follow_redirects=True)

    assert response.status_code == 200
    assert b'User not found' in response.data


def test_login_rejects_invalid_password():
    with app.app_context():
        user = User(first_name='Test', last_name='User', email='wrongpass@test.com', role='team')
        user.set_password('secret123')
        db.session.add(user)
        db.session.commit()

    client = app.test_client()
    response = client.post('/login', data={'email': 'wrongpass@test.com', 'password': 'badpass'}, follow_redirects=True)

    assert response.status_code == 200
    assert b'Invalid password' in response.data


def test_pending_registration_must_be_verified_before_login():
    client = app.test_client()

    response = client.post('/register', data={
        'first_name': 'Verify',
        'last_name': 'User',
        'email': 'verify@test.com',
        'phone_country_code': '+380',
        'phone_number': '501112233',
        'password': 'secret123',
        'confirm_password': 'secret123'
    }, follow_redirects=False)

    assert response.status_code == 302

    with app.app_context():
        user = User.query.filter_by(email='verify@test.com').first()
        assert user is not None
        assert user.is_verified is False
        assert user.verification_token
        token = user.verification_token

    response = client.post('/login', data={
        'email': 'verify@test.com',
        'password': 'secret123'
    }, follow_redirects=True)

    assert response.status_code == 200
    assert b'Please verify your email first' in response.data

    response = client.get(f'/verify/{token}', follow_redirects=False)
    assert response.status_code == 302
    assert response.headers['Location'].endswith('/login')

    response = client.post('/login', data={
        'email': 'verify@test.com',
        'password': 'secret123'
    }, follow_redirects=False)

    with app.app_context():
        user = User.query.filter_by(email='verify@test.com').first()
        assert user.is_verified is True
        assert user.verification_token is None

    assert response.status_code == 302
    assert response.headers['Location'].endswith(f'/user/{user.id}')


def test_cancel_registration_deletes_pending_user():
    client = app.test_client()

    client.post('/register', data={
        'first_name': 'Cancel',
        'last_name': 'User',
        'email': 'cancel@test.com',
        'phone_country_code': '+380',
        'phone_number': '501112234',
        'password': 'secret123',
        'confirm_password': 'secret123'
    })

    with app.app_context():
        token = User.query.filter_by(email='cancel@test.com').first().verification_token

    response = client.get(f'/verify/cancel/{token}', follow_redirects=False)

    assert response.status_code == 302
    with app.app_context():
        assert User.query.filter_by(email='cancel@test.com').first() is None


def test_over_admin_can_login_with_initial_admin_key_password():
    from backend.auth import OVER_ADMIN_EMAIL, ensure_over_admin_user, _load_admin_key_value

    with app.app_context():
        from backend.models import Settings
        Settings.query.filter_by(key='over_admin_password_initialized').delete()
        Settings.query.filter_by(key='over_admin_enabled').delete()
        User.query.filter_by(email=OVER_ADMIN_EMAIL).delete()
        db.session.commit()
        db.session.add(Settings(key='over_admin_enabled', value='1'))
        db.session.commit()
        over_admin = ensure_over_admin_user()
        over_admin_id = over_admin.id
        password = _load_admin_key_value()

    client = app.test_client()
    response = client.post('/login', data={
        'email': OVER_ADMIN_EMAIL,
        'password': password
    }, follow_redirects=False)

    assert response.status_code == 302
    assert response.headers['Location'].endswith(f'/user/{over_admin_id}')

    with client.session_transaction() as sess:
        assert sess['user_id'] == over_admin_id

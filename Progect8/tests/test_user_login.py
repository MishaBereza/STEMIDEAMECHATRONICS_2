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
        db.session.add(user)
        db.session.commit()
        user_id = user.id

    client = app.test_client()
    response = client.post('/login', data={'email': 'login@test.com'}, follow_redirects=False)

    assert response.status_code == 302
    assert response.headers['Location'].endswith(f'/user/{user_id}')

    with client.session_transaction() as sess:
        assert sess['user_id'] == user_id


def test_login_shows_error_for_missing_user():
    client = app.test_client()
    response = client.post('/login', data={'email': 'missing@test.com'}, follow_redirects=True)

    assert response.status_code == 200
    assert b'User not found' in response.data

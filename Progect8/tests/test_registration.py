import os, sys
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import pytest
from backend.app import app, db
from backend.auth import register_user
from backend.teams import register_team
from backend.admin import user_profile
from backend.models import User, Tournament, Team
from flask import get_flashed_messages


def setup_module(module):
    # reset database before tests
    with app.app_context():
        db.drop_all()
        db.create_all()


def test_user_registration_uniqueness():
    with app.test_request_context('/register', method='POST', data={
        'first_name': 'John',
        'last_name': 'Doe',
        'email': 'john@example.com'
    }):
        register_user()
    # second with same name should be rejected
    with app.test_request_context('/register', method='POST', data={
        'first_name': 'John',
        'last_name': 'Doe',
        'email': 'john2@example.com'
    }):
        register_user()
    with app.app_context():
        users = User.query.all()
        assert len(users) == 1


def test_team_registration_requires_registered():
    with app.app_context():
        # create tournament and users
        t = Tournament(name='Cup', description='')
        db.session.add(t)
        db.session.commit()
        u1 = User(first_name='A', last_name='B', email='a@x.com')
        u2 = User(first_name='C', last_name='D', email='c@x.com')
        db.session.add_all([u1, u2])
        db.session.commit()
        tid = t.id

    # valid registration
    with app.test_request_context(f'/tournament/{tid}/register', method='POST', data={
        'name': 'TeamOne',
        'captain_email': 'a@x.com',
        'members': 'c@x.com'
    }):
        register_team(tid)
    with app.app_context():
        teams = Team.query.all()
        assert len(teams) == 1
        team = teams[0]
        assert team.captain.email == 'a@x.com'
        assert team.members.count() == 1
        assert team.members.first().email == 'c@x.com'

    # duplicate member email should be rejected (no new team added)
    with app.test_request_context(f'/tournament/{tid}/register', method='POST', data={
        'name': 'TeamTwo',
        'captain_email': 'a@x.com',
        'members': 'c@x.com,c@x.com'
    }):
        register_team(tid)
    with app.app_context():
        assert Team.query.count() == 1


def test_profile_page_lists_teams():
    with app.app_context():
        # use existing users/teams; skip if none (avoids creating test data)
        u = User.query.filter_by(email='a@x.com').first()
        if not u:
            pytest.skip('no user a@x.com available; run full suite instead')
        with app.test_request_context(f'/user/{u.id}'):
            html = user_profile(u.id)
        assert 'TeamOne' in html
        assert 'Teams as Captain' in html

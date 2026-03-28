import os, sys
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from backend.app import app, db
from backend.models import User, Tournament, Team


def setup_module(module):
    with app.app_context():
        db.drop_all()
        db.create_all()


def test_admin_delete_user_and_team():
    with app.app_context():
        # create users and tournament
        u1 = User(first_name='Cap', last_name='One', email='cap1@example.com')
        u2 = User(first_name='Mem', last_name='One', email='mem1@example.com')
        db.session.add_all([u1, u2])
        db.session.commit()
        t = Tournament(name='TDel', description='')
        db.session.add(t)
        db.session.commit()
        team = Team(name='TeamDel', captain_id=u1.id, tournament_id=t.id)
        db.session.add(team)
        db.session.commit()
        team.members.append(u2)
        db.session.commit()

        # delete member user
        from backend.admin import admin_delete_user
        from flask import session
        with app.test_request_context(method='POST'):
            session['admin'] = True
            resp = admin_delete_user(u2.id)
        # user should be gone
        assert User.query.filter_by(email='mem1@example.com').first() is None

        # delete team
        from backend.admin import admin_delete_team
        with app.test_request_context(method='POST'):
            session['admin'] = True
            resp = admin_delete_team(team.id)
        assert db.session.get(Team, team.id) is None

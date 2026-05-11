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


def test_super_admin_cannot_be_deleted_or_demoted():
    from backend.auth import ensure_over_admin_user
    from backend.admin import admin_delete_user, change_user_role
    from flask import session

    with app.app_context():
        super_admin = ensure_over_admin_user()
        super_admin_id = super_admin.id

    with app.test_request_context(method='POST'):
        session['admin'] = True
        admin_delete_user(super_admin_id)

    with app.app_context():
        super_admin = db.session.get(User, super_admin_id)
        assert super_admin is not None
        assert super_admin.role == 'admin'

    with app.test_request_context(method='POST', data={'role': 'team'}):
        session['admin'] = True
        change_user_role(super_admin_id)

    with app.app_context():
        super_admin = db.session.get(User, super_admin_id)
        assert super_admin is not None
        assert super_admin.role == 'admin'


def test_regular_admin_can_be_deleted():
    from backend.admin import admin_delete_user
    from flask import session

    with app.app_context():
        User.query.filter_by(email='delete-admin@example.com').delete()
        admin = User(
            first_name='Delete',
            last_name='Admin',
            email='delete-admin@example.com',
            role='admin',
            is_verified=True,
        )
        db.session.add(admin)
        db.session.commit()
        admin_id = admin.id

    with app.test_request_context(method='POST'):
        session['admin'] = True
        admin_delete_user(admin_id)

    with app.app_context():
        assert db.session.get(User, admin_id) is None

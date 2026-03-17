import os, sys
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app import app, db
from backend.models import Tournament, Team, User, Round, Submission, Evaluation


def setup_module(module):
    with app.app_context():
        db.drop_all()
        db.create_all()


def test_delete_tournament_cascades():
    with app.app_context():
        # create tournament with one round, team, users, submission
        t = Tournament(name='DelCup', description='')
        db.session.add(t)
        db.session.commit()
        r = Round(tournament_id=t.id, title='R1')
        db.session.add(r)
        u1 = User(first_name='X', last_name='Y', email='x@y.com')
        u2 = User(first_name='A', last_name='B', email='a@b.com')
        db.session.add_all([u1, u2])
        db.session.commit()
        team = Team(name='T', captain_id=u1.id, tournament_id=t.id)
        db.session.add(team)
        db.session.commit()
        team.members.append(u2)
        db.session.commit()

        # now delete tournament using function directly
        from app import delete_tournament
        # simulate admin session for call
        from flask import session
        with app.test_request_context(method='POST'):
            session['admin'] = True
            resp = delete_tournament(t.id)
        # check db state
        assert Tournament.query.get(t.id) is None
        assert Team.query.filter_by(tournament_id=t.id).count() == 0
        # membership associations should be gone (no rows in team_members)
        from backend.models import team_members
        res = db.session.execute(team_members.select()).fetchall()
        assert res == []

import os, sys
import werkzeug

# some Werkzeug releases no longer expose __version__ attribute which
# Flask's testing utilities expect when constructing the test_client. Add
# a dummy version to avoid AttributeError in our tests.
if not hasattr(werkzeug, '__version__'):
    werkzeug.__version__ = '2.3.0'

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from backend.app import app, db
from backend.models import User, Tournament, Team
from flask import session


def setup_module(module):
    with app.app_context():
        db.drop_all()
        db.create_all()


def login_as_admin(client):
    with client.session_transaction() as sess:
        sess['admin'] = True


def test_admin_teams_page_shows_submission_and_actions():
    with app.app_context():
        # prepare data
        t = Tournament(name='SubTour', description='', status='Submission')
        db.session.add(t)
        db.session.commit()
        tid = t.id
        # create a captain
        cap = User(first_name='Cap', last_name='Submit', email='cap@example.com')
        db.session.add(cap)
        db.session.commit()
        team = Team(name='SubTeam', captain_id=cap.id, tournament_id=tid,
                    repo_url='https://repo', live_url='https://live', comments='notes',
                    submission_status='Pending')
        db.session.add(team)
        db.session.commit()

    from backend.admin import admin_tournament_teams
    # call the view function within a request context
    with app.test_request_context(f'/admin/tournament/{tid}/teams'):
        session['admin'] = True
        data = admin_tournament_teams(tid)
    assert 'SubTeam' in data
    assert 'https://repo' in data
    assert 'https://live' in data
    assert 'notes' in data
    assert 'Pending' in data
    # acceptance buttons should be visible
    assert 'Accept' in data
    assert 'Reject' in data
    assert 'Return' in data


def test_admin_decision_changes_status():
    # create a fresh tournament and team for this test
    with app.app_context():
        t = Tournament(name='SubTour2', description='', status='Submission')
        db.session.add(t)
        db.session.commit()
        tid = t.id
        cap = User(first_name='Cap2', last_name='Submit', email='cap2@example.com')
        db.session.add(cap)
        db.session.commit()
        team = Team(name='SubTeam2', captain_id=cap.id, tournament_id=tid,
                    repo_url='https://repo2', live_url='https://live2', comments='notes2',
                    submission_status='Pending')
        db.session.add(team)
        db.session.commit()
        teamid = team.id

    from backend.admin import admin_team_decide, admin_tournament_teams
    # simulate POST decision
    with app.test_request_context(f'/admin/team/{teamid}/decide', method='POST', data={'decision':'accept'}):
        session['admin'] = True
        resp = admin_team_decide(teamid)
    # the response should be a redirect
    assert resp.status_code in (301, 302)
    with app.app_context():
        team = Team.query.get(teamid)
        assert team.submission_status == 'Accepted'

    # check tournament teams page again
    with app.test_request_context(f'/admin/tournament/{tid}/teams'):
        session['admin'] = True
        data = admin_tournament_teams(tid)
    assert 'Accepted' in data
    assert 'Accept' not in data or data.count('Accept') < 2  # header may include word

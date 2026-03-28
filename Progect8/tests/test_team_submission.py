import os, sys
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from backend.app import app, db
from backend.models import User, Tournament, Team
from flask import session


def setup_module(module):
    with app.app_context():
        db.drop_all()
        db.create_all()


def create_team_for_status(tname='TeamX', tour_status='Submission'):
    # create a unique tournament/user/team so multiple calls do not conflict
    with app.app_context():
        t = Tournament(name=f'Tour_{tname}', description='', status=tour_status)
        db.session.add(t)
        db.session.commit()
        tid = t.id
        cap = User(first_name=f'Cap_{tname}', last_name='User', email=f'cap_{tname.lower()}@example.com')
        db.session.add(cap)
        db.session.commit()
        capid = cap.id
        team = Team(name=tname, captain_id=capid, tournament_id=tid)
        db.session.add(team)
        db.session.commit()
        teamid = team.id
        return teamid, tid, capid


def login(client, uid=None, admin=False):
    with client.session_transaction() as sess:
        if admin:
            sess['admin'] = True
        if uid:
            sess['user_id'] = uid


def test_captain_can_save_and_submit():
    teamid, tid, capid = create_team_for_status()
    # use request context to call view directly
    from backend.teams import team_page
    # save links
    with app.test_request_context(f'/team/{teamid}', method='POST', data={
        'repo_url': 'https://repo1',
        'live_url': 'https://live1',
        'comments': 'first',
        'action': 'save'
    }):
        session['user_id'] = capid
        db.session.expire_all()
        resp = team_page(teamid)
    # after save we expect html response
    assert 'Saved' in resp
    with app.app_context():
        team = db.session.get(Team, teamid)
        assert team.repo_url == 'https://repo1'
        assert team.submission_status != 'Pending'
    # now submit
    with app.test_request_context(f'/team/{teamid}', method='POST', data={
        'repo_url': 'https://repo1',
        'live_url': 'https://live1',
        'comments': 'first',
        'action': 'send'
    }):
        session['user_id'] = capid
        db.session.expire_all()
        resp = team_page(teamid)
    assert 'Submitted' in resp
    with app.app_context():
        team = db.session.get(Team, teamid)
        assert team.submission_status == 'Pending'

    # change tournament to Running and verify captain can still save and submit
    with app.app_context():
        t = db.session.get(Tournament, tid)
        t.status = 'Running'
        db.session.commit()
    # save under running
    with app.test_request_context(f'/team/{teamid}', method='POST', data={
        'repo_url': 'https://repo2',
        'live_url': 'https://live2',
        'comments': 'second',
        'action': 'save'
    }):
        session['user_id'] = capid
        db.session.expire_all()
        resp2 = team_page(teamid)
    assert 'Saved' in resp2
    with app.app_context():
        team = db.session.get(Team, teamid)
        assert team.repo_url == 'https://repo2'
    with app.test_request_context(f'/team/{teamid}', method='POST', data={
        'repo_url': 'https://repo2',
        'live_url': 'https://live2',
        'comments': 'second',
        'action': 'send'
    }):
        session['user_id'] = capid
        db.session.expire_all()
        resp3 = team_page(teamid)
    assert 'Submitted' in resp3
    with app.app_context():
        team = db.session.get(Team, teamid)
        assert team.submission_status == 'Pending'

        # captain can edit members list via POST
        with app.test_request_context(f'/team/{teamid}', method='POST', data={
            'repo_url': 'https://repo3',
            'live_url': '',
            'members': 'newuser@example.com',
            'action': 'save'
        }):
            session['user_id'] = capid
            db.session.expire_all()
            resp4 = team_page(teamid)
        assert 'Saved' in resp4
        # new member not yet registered so should not add
        with app.app_context():
            team = db.session.get(Team, teamid)
            assert team.members.count() == 0

        # register new member and add again
        with app.app_context():
            u = User(first_name='New', last_name='User', email='newuser@example.com')
            db.session.add(u)
            db.session.commit()
        with app.test_request_context(f'/team/{teamid}', method='POST', data={
            'repo_url': 'https://repo3',
            'live_url': '',
            'members': 'newuser@example.com',
            'action': 'save'
        }):
            session['user_id'] = capid
            db.session.expire_all()
            resp5 = team_page(teamid)
        assert 'Saved' in resp5
        with app.app_context():
            team = db.session.get(Team, teamid)
            assert team.members.count() == 1
            assert team.members.first().email == 'newuser@example.com'


def test_member_can_save_but_not_submit():
    # create team and add a member
    teamid, tid, capid = create_team_for_status(tname='TeamY')
    with app.app_context():
        member = User(first_name='Member', last_name='User', email='member@example.com')
        db.session.add(member)
        db.session.commit()
        team = db.session.get(Team, teamid)
        team.members.append(member)
        db.session.commit()
        member_id = member.id
    from backend.teams import team_page
    # member should be able to save but not send
    with app.test_request_context(f'/team/{teamid}', method='POST', data={
        'repo_url':'x','live_url':'y','comments':'c','action':'save'
    }):
        session['user_id'] = member_id
        db.session.expire_all()
        resp = team_page(teamid)
    assert 'Saved' in resp
    with app.app_context():
        t2 = db.session.get(Team, teamid)
        assert t2.repo_url == 'x'
        assert t2.submission_status != 'Pending'
    # attempt to submit should not change status
    with app.test_request_context(f'/team/{teamid}', method='POST', data={
        'repo_url':'x','live_url':'y','comments':'c','action':'send'
    }):
        session['user_id'] = member_id
        db.session.expire_all()
        resp2 = team_page(teamid)
    assert 'Submitted' not in resp2
    with app.app_context():
        t3 = db.session.get(Team, teamid)
        assert t3.submission_status != 'Pending'


def test_no_form_when_not_submission():
    teamid, tid, capid = create_team_for_status(tour_status='Registration', tname='TeamZ')
    from backend.teams import team_page
    with app.test_request_context(f'/team/{teamid}', method='GET'):
        session['user_id'] = capid
        resp_html = team_page(teamid)
    # after status not submission the form should not be present
    assert '<form' not in resp_html

def test_auto_submit_on_finished():
    # create tournament/team without any submission status
    with app.app_context():
        t = Tournament(name='Auto', description='', status='Running')
        db.session.add(t)
        db.session.commit()
        cap = User(first_name='CapA', last_name='Auto', email='capa@example.com')
        db.session.add(cap)
        db.session.commit()
        team = Team(name='AutoTeam', captain_id=cap.id, tournament_id=t.id)
        db.session.add(team)
        db.session.commit()
        teamid = team.id
        tid2 = t.id
        capid = cap.id
    # change status to finished and visit page
    client = app.test_client()
    login(client, capid)
    with app.app_context():
        t = db.session.get(Tournament, tid2)
        t.status = 'Finished'
        db.session.commit()
    resp = client.get(f'/team/{teamid}')
    assert b'Status:' in resp.data
    assert b'Submitted' in resp.data

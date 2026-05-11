import os, sys
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from backend.app import app, db
from backend.models import User, Tournament, Round, Team, Submission
from flask import session


def setup_module(module):
    with app.app_context():
        db.drop_all()
        db.create_all()


def create_tournament_and_round(status='Submission'):
    with app.app_context():
        t = Tournament(name='Tourney', description='', status=status)
        db.session.add(t)
        db.session.commit()
        r = Round(tournament_id=t.id, title='R1')
        db.session.add(r)
        db.session.commit()
        return t.id, r.id


def login(client, uid=None, admin=False):
    with client.session_transaction() as sess:
        if admin:
            sess['admin'] = True
        if uid:
            sess['user_id'] = uid


def test_round_submit_membership_and_repo():
    # default status = Submission
    tid, rid = create_tournament_and_round()
    with app.app_context():
        cap = User(first_name='Captain', last_name='One', email='cap1@example.com')
        other = User(first_name='Other', last_name='User', email='other@example.com')
        db.session.add_all([cap, other])
        db.session.commit()
        team = Team(name='TeamA', captain_id=cap.id, tournament_id=tid)
        db.session.add(team)
        db.session.commit()
        cap_id = cap.id
        other_id = other.id
        team_id = team.id

    client = app.test_client()
    # other user should not see form
    login(client, other_id)
    resp = client.get(f'/round/{rid}/submit')
    assert b'not a member' in resp.data
    # tournament page should not show submit link for non-members
    resp2 = client.get(f'/tournament/{tid}')
    assert b'/round/' not in resp2.data or b'submit' not in resp2.data

    # captain sees form and repo field required
    login(client, cap_id)
    resp = client.get(f'/round/{rid}/submit')
    assert b'<form' in resp.data
    assert b'name="repo_url"' in resp.data
    assert b'required' in resp.data
    # tournament page should show submit link for captain
    resp3 = client.get(f'/tournament/{tid}')
    assert b'/round/' in resp3.data and b'submit' in resp3.data

    # change tournament to Running and repeat check
    with app.app_context():
        t = db.session.get(Tournament, tid)
        t.status = 'Running'
        db.session.commit()
    resp4 = client.get(f'/round/{rid}/submit')
    assert b'<form' in resp4.data
    resp5 = client.get(f'/tournament/{tid}')
    assert b'/round/' in resp5.data and b'submit' in resp5.data

    # submitting without repo yields warning
    resp = client.post(f'/round/{rid}/submit', data={
        'team_id': team_id,
        'repo_url': '',
        'demo_url': 'http://demo',
        'description': 'desc'
    }, follow_redirects=True)
    assert b'GitHub repo URL is required' in resp.data

    # valid submission
    resp = client.post(f'/round/{rid}/submit', data={
        'team_id': team_id,
        'repo_url': 'https://repo',
        'demo_url': '',
        'description': ''
    }, follow_redirects=True)
    assert b'Submitted' in resp.data
    with app.app_context():
        s = Submission.query.filter_by(team_id=team_id, round_id=rid).first()
        assert s is not None

    # create another team and ensure captain1 still cannot submit for it
    with app.app_context():
        cap2 = User(first_name='Captain', last_name='Two', email='capX@example.com')
        db.session.add(cap2)
        db.session.commit()
        team2 = Team(name='TeamOther', captain_id=cap2.id, tournament_id=tid)
        db.session.add(team2)
        db.session.commit()
        team2_id = team2.id
    resp = client.post(f'/round/{rid}/submit', data={
        'team_id': team2_id,
        'repo_url': 'https://repo',
        'demo_url': '',
        'description': ''
    }, follow_redirects=True)
    assert b'not allowed' in resp.data
    with app.app_context():
        s2 = Submission.query.filter_by(team_id=team2_id, round_id=rid).first()
        assert s2 is None


def test_submission_only_in_submission_status():
    tid, rid = create_tournament_and_round(status='Registration')
    with app.app_context():
        cap = User(first_name='Captain', last_name='Two', email='cap2@example.com')
        db.session.add(cap)
        db.session.commit()
        team = Team(name='TeamB', captain_id=cap.id, tournament_id=tid)
        db.session.add(team)
        db.session.commit()
        cap_id = cap.id
        team_id = team.id

    client = app.test_client()
    login(client, cap_id)
    resp = client.get(f'/round/{rid}/submit')
    # should inform not open
    assert b'Submissions are not open' in resp.data
    # posting should also flash warning and redirect to tournament page
    resp2 = client.post(f'/round/{rid}/submit', data={
        'team_id': team_id,
        'repo_url': 'https://repo',
    }, follow_redirects=True)
    assert b'Submissions are not open' in resp2.data


def test_round_submit_hides_foreign_teams_after_stale_admin_session_is_cleared_by_login():
    tid, rid = create_tournament_and_round()
    with app.app_context():
        captain = User(first_name='Captain', last_name='Own', email='owncap@example.com')
        member = User(first_name='Member', last_name='Own', email='ownmember@example.com')
        outsider = User(first_name='Captain', last_name='Other', email='othercap@example.com')
        captain.set_password('secret123')
        member.set_password('secret123')
        outsider.set_password('secret123')
        db.session.add_all([captain, member, outsider])
        db.session.commit()

        own_team = Team(name='Own Team', captain_id=captain.id, tournament_id=tid)
        db.session.add(own_team)
        db.session.flush()
        own_team.members.append(member)
        foreign_team = Team(name='Foreign Team', captain_id=outsider.id, tournament_id=tid)
        db.session.add(foreign_team)
        db.session.commit()

    client = app.test_client()
    with client.session_transaction() as sess:
        sess['admin'] = True
        sess['admin_user_id'] = 777

    login_response = client.post('/login', data={'email': 'ownmember@example.com', 'password': 'secret123'}, follow_redirects=False)
    assert login_response.status_code == 302

    response = client.get(f'/round/{rid}/submit')

    assert response.status_code == 200
    assert b'Own Team' in response.data
    assert b'Foreign Team' not in response.data


def test_admin_cannot_submit_for_foreign_team_without_membership():
    tid, rid = create_tournament_and_round()
    with app.app_context():
        admin = User(first_name='Admin', last_name='Viewer', email='adminviewer@example.com', role='admin')
        admin.set_password('secret123')
        captain = User(first_name='Captain', last_name='Only', email='captainonly@example.com')
        db.session.add_all([admin, captain])
        db.session.commit()

        team = Team(name='Protected Team', captain_id=captain.id, tournament_id=tid)
        db.session.add(team)
        db.session.commit()
        admin_id = admin.id
        team_id = team.id

    client = app.test_client()
    login(client, admin_id, admin=True)

    response = client.get(f'/round/{rid}/submit')
    assert b'Protected Team' not in response.data

    post_response = client.post(f'/round/{rid}/submit', data={
        'team_id': team_id,
        'repo_url': 'https://repo',
        'demo_url': '',
        'description': ''
    }, follow_redirects=True)
    assert b'not allowed' in post_response.data


def test_tournament_with_no_rounds_shows_attach():
    # create tournament with no rounds
    with app.app_context():
        t = Tournament(name='Empty', description='', status='Registration')
        db.session.add(t)
        db.session.commit()
        tid = t.id
    client = app.test_client()
    resp = client.get(f'/tournament/{tid}')
    assert b'Attach' in resp.data or b'\xd0\x9f\xd1\x80\xd0\xb8\xd0\xba\xd1\x80\xd0\xb5\xd0\xbf\xd0\xb8\xd1\x82\xd0\xb8' in resp.data

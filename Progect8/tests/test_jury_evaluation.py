import os
import sys
from datetime import datetime, timedelta

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from backend.app import app, db
from backend.models import Evaluation, Submission, Team, Tournament, User, Round


def setup_module(module):
    with app.app_context():
        db.drop_all()
        db.create_all()


def setup_function(function):
    with app.app_context():
        db.drop_all()
        db.create_all()


def create_submission_fixture():
    with app.app_context():
        jury = User(first_name='Jury', last_name='Judge', email='jury@test.com', role='jury')
        captain = User(first_name='Cap', last_name='One', email='cap@test.com', role='team')
        tournament = Tournament(name='Eval Cup', description='', status='Running')
        db.session.add_all([jury, captain, tournament])
        db.session.commit()

        tournament.assigned_juries.append(jury)
        db.session.commit()

        team = Team(name='Team Eval', captain_id=captain.id, tournament_id=tournament.id)
        db.session.add(team)
        db.session.commit()

        round_item = Round(
            tournament_id=tournament.id,
            title='Round 1',
            level=1,
            status='Closed',
            end_at=datetime.utcnow() - timedelta(hours=1)
        )
        db.session.add(round_item)
        db.session.commit()

        submission = Submission(
            team_id=team.id,
            round_id=round_item.id,
            repo_url='https://github.com/example/repo',
            description='Submission for evaluation'
        )
        db.session.add(submission)
        db.session.commit()

        return jury.id, submission.id


def test_evaluate_submission_saves_ten_scores_and_redirects():
    jury_id, submission_id = create_submission_fixture()
    client = app.test_client()

    with client.session_transaction() as sess:
        sess['jury_id'] = jury_id

    response = client.post(
        f'/evaluate/{submission_id}',
        data={
            'score1': '1',
            'score2': '2',
            'score3': '3',
            'score4': '4',
            'score5': '5',
            'score6': '6',
            'score7': '7',
            'score8': '8',
            'score9': '9',
            'score10': '10',
            'comment': 'Looks solid'
        },
        follow_redirects=False
    )

    assert response.status_code == 302
    assert response.headers['Location'].endswith('/jury/evaluate')

    with app.app_context():
        evaluation = Evaluation.query.filter_by(submission_id=submission_id, jury_id=jury_id).one()
        assert evaluation.score1 == 1
        assert evaluation.score10 == 10
        assert evaluation.score_tech == 55
        assert evaluation.score_func is None
        assert evaluation.score_ui is None
        assert evaluation.comment == 'Looks solid'


def test_evaluate_submission_rejects_invalid_score():
    jury_id, submission_id = create_submission_fixture()
    client = app.test_client()

    with client.session_transaction() as sess:
        sess['jury_id'] = jury_id

    response = client.post(
        f'/evaluate/{submission_id}',
        data={
            'score1': '11',
            'score2': '2',
            'score3': '3',
            'score4': '4',
            'score5': '5',
            'score6': '6',
            'score7': '7',
            'score8': '8',
            'score9': '9',
            'score10': '10',
            'comment': 'Too high'
        },
        follow_redirects=True
    )

    assert response.status_code == 200
    assert b'score1 must be between 0 and 10' in response.data

    with app.app_context():
        evaluation = Evaluation.query.filter_by(submission_id=submission_id, jury_id=jury_id).first()
        assert evaluation is None


def test_jury_sees_only_assigned_tournament_submissions():
    with app.app_context():
        jury = User(first_name='Assigned', last_name='Jury', email='assigned@test.com', role='jury')
        captain = User(first_name='Cap', last_name='Two', email='captwo@test.com', role='team')
        visible_tournament = Tournament(name='Visible Cup', description='', status='Running')
        hidden_tournament = Tournament(name='Hidden Cup', description='', status='Running')
        db.session.add_all([jury, captain, visible_tournament, hidden_tournament])
        db.session.commit()

        visible_tournament.assigned_juries.append(jury)
        db.session.commit()

        visible_team = Team(name='Visible Team', captain_id=captain.id, tournament_id=visible_tournament.id)
        hidden_team = Team(name='Hidden Team', captain_id=captain.id, tournament_id=hidden_tournament.id)
        db.session.add_all([visible_team, hidden_team])
        db.session.commit()

        visible_round = Round(
            tournament_id=visible_tournament.id,
            title='Visible Round',
            level=1,
            status='Closed',
            end_at=datetime.utcnow() - timedelta(hours=1)
        )
        hidden_round = Round(
            tournament_id=hidden_tournament.id,
            title='Hidden Round',
            level=1,
            status='Closed',
            end_at=datetime.utcnow() - timedelta(hours=1)
        )
        db.session.add_all([visible_round, hidden_round])
        db.session.commit()

        db.session.add_all([
            Submission(team_id=visible_team.id, round_id=visible_round.id, repo_url='https://github.com/example/visible'),
            Submission(team_id=hidden_team.id, round_id=hidden_round.id, repo_url='https://github.com/example/hidden'),
        ])
        db.session.commit()

        jury_id = jury.id

    client = app.test_client()
    with client.session_transaction() as sess:
        sess['jury_id'] = jury_id

    response = client.get('/jury/evaluate')

    assert response.status_code == 200
    assert b'Visible Team' in response.data
    assert b'Hidden Team' not in response.data


def test_jury_sees_assigned_tournament_submissions_even_with_unexpected_status():
    with app.app_context():
        jury = User(first_name='Status', last_name='Jury', email='statusjury@test.com', role='jury')
        captain = User(first_name='Cap', last_name='Three', email='capthree@test.com', role='team')
        tournament = Tournament(name='Status Cup', description='', status='Active')
        db.session.add_all([jury, captain, tournament])
        db.session.commit()

        tournament.assigned_juries.append(jury)
        db.session.commit()

        team = Team(name='Status Team', captain_id=captain.id, tournament_id=tournament.id)
        db.session.add(team)
        db.session.commit()

        round_item = Round(
            tournament_id=tournament.id,
            title='Status Round',
            level=1,
            status='Closed',
            end_at=datetime.utcnow() - timedelta(hours=1)
        )
        db.session.add(round_item)
        db.session.commit()

        db.session.add(Submission(team_id=team.id, round_id=round_item.id, repo_url='https://github.com/example/status'))
        db.session.commit()

        jury_id = jury.id

    client = app.test_client()
    with client.session_transaction() as sess:
        sess['jury_id'] = jury_id

    response = client.get('/jury/evaluate')

    assert response.status_code == 200
    assert b'Status Team' in response.data


def test_assigned_admin_sees_own_name_and_assigned_submissions_in_jury_panel():
    with app.app_context():
        admin = User(first_name='Real', last_name='Admin', email='realadmin@test.com', role='admin', is_verified=True)
        admin.set_password('secret123')
        captain = User(first_name='Cap', last_name='Four', email='capfour@test.com', role='team')
        tournament = Tournament(name='Admin Cup', description='', status='Running')
        db.session.add_all([admin, captain, tournament])
        db.session.commit()

        tournament.assigned_juries.append(admin)
        db.session.commit()

        team = Team(name='Admin Team', captain_id=captain.id, tournament_id=tournament.id)
        db.session.add(team)
        db.session.commit()

        round_item = Round(
            tournament_id=tournament.id,
            title='Admin Round',
            level=1,
            status='Closed',
            end_at=datetime.utcnow() - timedelta(hours=1)
        )
        db.session.add(round_item)
        db.session.commit()

        db.session.add(Submission(team_id=team.id, round_id=round_item.id, repo_url='https://github.com/example/admin'))
        db.session.commit()

        admin_id = admin.id

    client = app.test_client()
    with client.session_transaction() as sess:
        sess['admin'] = True
        sess['admin_user_id'] = admin_id
        sess['user_id'] = admin_id

    response = client.get('/jury/evaluate')

    assert response.status_code == 200
    assert b'Real Admin' in response.data
    assert b'Super Admin' not in response.data
    assert b'Admin Team' in response.data


def test_jury_does_not_see_submissions_until_round_is_closed():
    with app.app_context():
        jury = User(first_name='Late', last_name='Jury', email='latejury@test.com', role='jury')
        captain = User(first_name='Cap', last_name='Five', email='capfive@test.com', role='team')
        tournament = Tournament(name='Late Cup', description='', status='Running')
        db.session.add_all([jury, captain, tournament])
        db.session.commit()

        tournament.assigned_juries.append(jury)
        db.session.commit()

        team = Team(name='Hidden Until Closed', captain_id=captain.id, tournament_id=tournament.id)
        db.session.add(team)
        db.session.commit()

        round_item = Round(
            tournament_id=tournament.id,
            title='Open Round',
            level=1,
            status='Active',
            end_at=datetime.utcnow() + timedelta(hours=1)
        )
        db.session.add(round_item)
        db.session.commit()

        db.session.add(Submission(team_id=team.id, round_id=round_item.id, repo_url='https://github.com/example/open'))
        db.session.commit()

        jury_id = jury.id

    client = app.test_client()
    with client.session_transaction() as sess:
        sess['jury_id'] = jury_id

    response = client.get('/jury/evaluate')

    assert response.status_code == 200
    assert b'Hidden Until Closed' not in response.data
    assert b'Evaluation has not started yet' in response.data


def test_direct_evaluation_is_blocked_until_round_is_closed():
    with app.app_context():
        jury = User(first_name='Block', last_name='Jury', email='blockjury@test.com', role='jury')
        captain = User(first_name='Cap', last_name='Six', email='capsix@test.com', role='team')
        tournament = Tournament(name='Blocked Cup', description='', status='Running')
        db.session.add_all([jury, captain, tournament])
        db.session.commit()

        tournament.assigned_juries.append(jury)
        db.session.commit()

        team = Team(name='Blocked Team', captain_id=captain.id, tournament_id=tournament.id)
        db.session.add(team)
        db.session.commit()

        round_item = Round(
            tournament_id=tournament.id,
            title='Blocked Round',
            level=1,
            status='Active',
            end_at=datetime.utcnow() + timedelta(hours=1)
        )
        db.session.add(round_item)
        db.session.commit()

        submission = Submission(team_id=team.id, round_id=round_item.id, repo_url='https://github.com/example/blocked')
        db.session.add(submission)
        db.session.commit()

        jury_id = jury.id
        submission_id = submission.id

    client = app.test_client()
    with client.session_transaction() as sess:
        sess['jury_id'] = jury_id

    response = client.get(f'/evaluate/{submission_id}', follow_redirects=True)

    assert response.status_code == 200
    assert b'Evaluation has not started yet' in response.data
    assert b'Blocked Team' not in response.data

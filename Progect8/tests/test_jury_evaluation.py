import os
import sys

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from backend.app import app, db
from backend.models import Evaluation, Submission, Team, Tournament, User


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

        submission = Submission(
            team_id=team.id,
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

        db.session.add_all([
            Submission(team_id=visible_team.id, repo_url='https://github.com/example/visible'),
            Submission(team_id=hidden_team.id, repo_url='https://github.com/example/hidden'),
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

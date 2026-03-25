from backend.app import app
from backend.models import db, User, Tournament, Round, Team, Submission, Evaluation
from datetime import datetime, timedelta

with app.app_context():
    db.create_all()
    # create admin and jury users
    if not User.query.filter_by(email='admin@example.com').first():
        admin = User(first_name='Admin', last_name='User', email='admin@example.com', role='admin')
        jury = User(first_name='Jury', last_name='Member', email='jury@example.com', role='jury')
        db.session.add_all([admin, jury])
    # create some team users
    if not User.query.filter_by(email='captain@demo.com').first():
        captain = User(first_name='Captain', last_name='Demo', email='captain@demo.com')
        member = User(first_name='Member', last_name='Demo', email='member@demo.com')
        db.session.add_all([captain, member])
    # create a demo tournament
    t = Tournament.query.filter_by(name='Demo Cup').first()
    if not t:
        t = Tournament(name='Demo Cup', description='Demo tournament', status='Running')
        db.session.add(t)
        db.session.flush()
        r = Round(tournament_id=t.id, title='Round 1', description='Initial round', level=1, status='Active', start_at=datetime.utcnow(), end_at=datetime.utcnow()+timedelta(days=1))
        db.session.add(r)
        db.session.flush()
        # create a sample team with captain and member
        if 'captain' in locals():
            team = Team(name='Demo Team', captain_id=captain.id, tournament_id=t.id,
                        repo_url='https://example.com/repo', live_url='https://example.com/live',
                        comments='Demo submission', submission_status='Pending')
            db.session.add(team)
            db.session.flush()
            team.members.append(member)
            # create a submission for the round
            submission = Submission(team_id=team.id, round_id=r.id, repo_url='https://github.com/demo/repo', description='Demo project description')
            db.session.add(submission)
            db.session.flush()
            # create a sample evaluation
            jury_user = User.query.filter_by(email='jury@example.com').first()
            if jury_user:
                evaluation = Evaluation(
                    submission_id=submission.id,
                    jury_id=jury_user.id,
                    score1=85, score2=90, score3=88, score4=92, score5=87,
                    score6=89, score7=91, score8=86, score9=93, score10=88,
                    comment='Excellent work, good presentation and code quality.'
                )
                db.session.add(evaluation)
    # Always set status to Finished for demo
    if t:
        t.status = 'Finished'
        db.session.commit()
    db.session.commit()
    print('Demo data created')

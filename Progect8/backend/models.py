from datetime import datetime
from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()

# Roles: admin, team, jury

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    first_name = db.Column(db.String(120), nullable=False)
    last_name = db.Column(db.String(120), nullable=False)
    email = db.Column(db.String(200), unique=True, nullable=False)
    age = db.Column(db.Integer)
    bio = db.Column(db.Text)
    role = db.Column(db.String(30), default='team')
    
    @property
    def name(self):
        return f"{self.first_name} {self.last_name}"


class Tournament(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    
    name = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text)

    max_teams = db.Column(db.Integer)

    status = db.Column(db.String(30), default="Draft")

    rounds = db.relationship('Round', backref='tournament', lazy=True)


# association table for many-to-many between teams and users (members)
team_members = db.Table('team_members',
    db.Column('team_id', db.Integer, db.ForeignKey('team.id'), primary_key=True),
    db.Column('user_id', db.Integer, db.ForeignKey('user.id'), primary_key=True)
)

class Team(db.Model):
    id = db.Column(db.Integer, primary_key=True)

    name = db.Column(db.String(200), nullable=False)
    # captain must be a registered user
    captain_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    captain = db.relationship('User', foreign_keys=[captain_id])

    # members relationship (excluding captain)
    members = db.relationship('User', secondary=team_members, backref='teams', lazy='dynamic')

    tournament_id = db.Column(db.Integer, db.ForeignKey('tournament.id'))

    submissions = db.relationship('Submission', backref='team', lazy=True)

    # contest‑wide submission data (links/comments)
    repo_url = db.Column(db.String(500))
    live_url = db.Column(db.String(500))
    comments = db.Column(db.Text)
    submitted_at = db.Column(db.DateTime)
    submission_status = db.Column(db.String(30), default='None')  # None, Pending, Accepted, Rejected, Returned


class Round(db.Model):
    id = db.Column(db.Integer, primary_key=True)

    tournament_id = db.Column(db.Integer, db.ForeignKey('tournament.id'))

    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text)
    must_have = db.Column(db.Text)

    start_at = db.Column(db.DateTime)
    end_at = db.Column(db.DateTime)

    level = db.Column(db.Integer, default=1)

    status = db.Column(db.String(30), default="Draft")

    submissions = db.relationship('Submission', backref='round', lazy=True)


class Submission(db.Model):
    id = db.Column(db.Integer, primary_key=True)

    team_id = db.Column(db.Integer, db.ForeignKey('team.id'))
    round_id = db.Column(db.Integer, db.ForeignKey('round.id'))

    repo_url = db.Column(db.String(500))
    demo_url = db.Column(db.String(500))
    description = db.Column(db.Text)

    submitted_at = db.Column(db.DateTime, default=datetime.utcnow)

    evaluations = db.relationship('Evaluation', backref='submission', lazy=True)


class Evaluation(db.Model):
    id = db.Column(db.Integer, primary_key=True)

    submission_id = db.Column(db.Integer, db.ForeignKey('submission.id'))
    jury_id = db.Column(db.Integer, db.ForeignKey('user.id'))

    score1 = db.Column(db.Float)
    score2 = db.Column(db.Float)
    score3 = db.Column(db.Float)
    score4 = db.Column(db.Float)
    score5 = db.Column(db.Float)
    score6 = db.Column(db.Float)
    score7 = db.Column(db.Float)
    score8 = db.Column(db.Float)
    score9 = db.Column(db.Float)
    score10 = db.Column(db.Float)

    comment = db.Column(db.Text)

    def total(self):
        parts = [p for p in (self.score1, self.score2, self.score3, self.score4, self.score5, self.score6, self.score7, self.score8, self.score9, self.score10) if p is not None]
        return sum(parts) if parts else 0
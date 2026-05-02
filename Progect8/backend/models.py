from datetime import datetime
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash

db = SQLAlchemy()

# Roles: admin, team, jury

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    first_name = db.Column(db.String(120), nullable=False)
    last_name = db.Column(db.String(120), nullable=False)
    email = db.Column(db.String(200), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False, default='')
    phone_country_code = db.Column(db.String(10), nullable=False, default='+380')
    phone_number = db.Column(db.String(30), nullable=False, default='')
    age = db.Column(db.Integer)
    bio = db.Column(db.Text)
    role = db.Column(db.String(30), default='team')
    
    # Email verification fields
    is_verified = db.Column(db.Boolean, default=False)
    verification_token = db.Column(db.String(64), unique=True, nullable=True)
    
    # Login notification fields
    last_login_at = db.Column(db.DateTime, nullable=True)
    login_token = db.Column(db.String(64), unique=True, nullable=True)
    
    @property
    def name(self):
        return f"{self.first_name} {self.last_name}"

    @property
    def phone_display(self):
        if self.phone_country_code and self.phone_number:
            return f"{self.phone_country_code} {self.phone_number}"
        return self.phone_number or ''

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return bool(self.password_hash) and check_password_hash(self.password_hash, password)


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

    tournament = db.relationship('Tournament', backref='teams', lazy=True)

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

    score_tech = db.Column(db.Float)
    score_func = db.Column(db.Float)
    score_ui = db.Column(db.Float)

    comment = db.Column(db.Text)
    
    # Relationship for criterion-based scores
    criterion_scores = db.relationship('EvaluationScore', backref='evaluation', lazy=True, cascade='all, delete-orphan')

    def total(self):
        # First try to get total from criterion scores
        criterion_total = sum([cs.score for cs in self.criterion_scores if cs.score is not None])
        if criterion_total > 0:
            return criterion_total
        
        # Fallback to old scoring system
        parts = [
            p for p in (
                self.score1, self.score2, self.score3, self.score4, self.score5,
                self.score6, self.score7, self.score8, self.score9, self.score10
            ) if p is not None
        ]
        if not parts:
            parts = [p for p in (self.score_tech, self.score_func, self.score_ui) if p is not None]
        return sum(parts) if parts else 0


class EvaluationScore(db.Model):
    """Score for a single evaluation criterion"""
    id = db.Column(db.Integer, primary_key=True)
    evaluation_id = db.Column(db.Integer, db.ForeignKey('evaluation.id'), nullable=False)
    criteria_id = db.Column(db.Integer, db.ForeignKey('evaluation_criteria.id'), nullable=False)
    
    criteria = db.relationship('EvaluationCriteria', lazy=True)
    score = db.Column(db.Float, nullable=False, default=0)


class EvaluationCriteria(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    tournament_id = db.Column(db.Integer, db.ForeignKey('tournament.id'), nullable=False)
    tournament = db.relationship('Tournament', backref='evaluation_criteria', lazy=True)
    
    name = db.Column(db.String(200))
    max_points = db.Column(db.Integer, default=10)
    order = db.Column(db.Integer, default=0)


class Settings(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    key = db.Column(db.String(100), unique=True, nullable=False)
    value = db.Column(db.Text, nullable=False)

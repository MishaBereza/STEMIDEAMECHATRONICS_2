from flask import render_template, request, redirect, url_for, flash, session
from .models import db, User
import os

ADMIN_PASSWORD_FILE = os.path.join(os.path.dirname(__file__), '..', 'admin_password.txt')

def get_or_create_admin_password():
    if os.path.exists(ADMIN_PASSWORD_FILE):
        with open(ADMIN_PASSWORD_FILE, 'r', encoding='utf-8') as f:
            return f.read().strip()
    default_pwd = 'admin123'
    with open(ADMIN_PASSWORD_FILE, 'w', encoding='utf-8') as f:
        f.write(default_pwd)
    return default_pwd

def load_admin_password():
    return get_or_create_admin_password()

def save_admin_password(new_password):
    with open(ADMIN_PASSWORD_FILE, 'w', encoding='utf-8') as f:
        f.write(new_password)

# ---------------- USER REGISTRATION ----------------
def register_user():
    if request.method == 'POST':
        first_name = request.form['first_name'].strip()
        last_name = request.form['last_name'].strip()
        email = request.form['email'].strip().lower()
        age = request.form.get('age')
        bio = request.form.get('bio','')

        # email unique check
        if User.query.filter_by(email=email).first():
            flash('User with that email already exists', 'warning')
            return redirect('/register')
        # combination of first+last name should also be unique (nicknames)
        if User.query.filter_by(first_name=first_name, last_name=last_name).first():
            flash('User with that name already exists', 'warning')
            return redirect('/register')

        user = User(
            first_name=first_name,
            last_name=last_name,
            email=email,
            age=int(age) if age else None,
            bio=bio,
            role='team'
        )

        db.session.add(user)
        db.session.commit()

        # set session so we can remember the user
        session['user_id'] = user.id

        flash('Registered successfully', 'success')
        return redirect('/')

    return render_template('register.html')

# ---------------- ADMIN LOGIN ----------------
def admin_panel():
    if request.method == 'POST':
        current_password = load_admin_password()
        if request.form.get('password') == current_password:
            session['admin'] = True
            return redirect('/admin/dashboard')
        else:
            flash('Невірний пароль', 'danger')
    return render_template('admin_login.html')

def admin_logout():
    session.pop('admin', None)
    return redirect('/')

def admin_change_password():
    if request.method == 'POST':
        new_password = request.form.get('new_password','').strip()
        confirm = request.form.get('confirm_password','').strip()
        if not new_password:
            flash('Password cannot be empty', 'warning')
        elif new_password != confirm:
            flash('Passwords do not match', 'warning')
        else:
            save_admin_password(new_password)
            flash('Admin password changed successfully', 'success')
            return redirect(url_for('admin_dashboard'))
    return render_template('admin_change_password.html')

# ---------------- JURY LOGIN ----------------
def jury_login():
    if request.method == 'POST':
        email = request.form.get('email', '').strip().lower()
        user = User.query.filter_by(email=email, role='jury').first()
        if user:
            session['jury_id'] = user.id
            flash('Logged in successfully as jury', 'success')
            return redirect('/jury/evaluate')  # Redirect to evaluation page
        else:
            flash('Invalid email or not a jury member', 'danger')
    return render_template('jury_login.html')

# ---------------- JURY EVALUATE ----------------
def jury_evaluate():
    if 'jury_id' not in session:
        return redirect('/jury/login')
    jury = User.query.get(session['jury_id'])
    if not jury or jury.role != 'jury':
        session.pop('jury_id', None)
        return redirect('/jury/login')

    from sqlalchemy import or_
    from .models import Submission, Evaluation, Team, Tournament, Round
    from datetime import datetime
    
    def sync_team_submissions(tournament):
        """Backfill Submission rows from team-level submits so jury can evaluate them."""
        if not tournament:
            return

        latest_round = Round.query.filter_by(tournament_id=tournament.id).order_by(Round.level.desc(), Round.id.desc()).first()
        round_id = latest_round.id if latest_round else None

        dirty = False
        teams_with_work = Team.query.filter(
            Team.tournament_id == tournament.id,
            Team.repo_url.isnot(None),
            Team.repo_url != ''
        ).all()

        for team in teams_with_work:
            submission_query = Submission.query.filter_by(team_id=team.id)
            if round_id is None:
                submission = submission_query.filter(Submission.round_id.is_(None)).first()
            else:
                submission = submission_query.filter_by(round_id=round_id).first()
            if submission:
                changed = False
                if not submission.repo_url and team.repo_url:
                    submission.repo_url = team.repo_url
                    changed = True
                if not submission.demo_url and team.live_url:
                    submission.demo_url = team.live_url
                    changed = True
                if not submission.description and team.comments:
                    submission.description = team.comments
                    changed = True
                dirty = dirty or changed
                continue

            db.session.add(Submission(
                team_id=team.id,
                round_id=round_id,
                repo_url=team.repo_url,
                demo_url=team.live_url,
                description=team.comments
            ))
            dirty = True

        if dirty:
            db.session.commit()

    candidate_tournaments = Tournament.query.filter(
        or_(
            Tournament.status.ilike('%finished%'),
            Tournament.status.ilike('%completed%'),
            Tournament.status.ilike('%closed%'),
            Tournament.status.ilike('%running%'),
            Tournament.status.ilike('%submission%'),
            Tournament.status.ilike('%registration%'),
            Tournament.status.ilike('%draft%')
        )
    ).order_by(Tournament.id.desc()).all()

    tournament = None
    for ct in candidate_tournaments:
        has_submission = Submission.query.join(Team, Submission.team_id == Team.id)\
            .filter(Team.tournament_id == ct.id).first()
        has_team_submit = Team.query.filter(
            Team.tournament_id == ct.id,
            Team.repo_url.isnot(None),
            Team.repo_url != ''
        ).first()
        if has_submission or has_team_submit:
            tournament = ct
            break

    if not tournament and candidate_tournaments:
        tournament = candidate_tournaments[0]

    if not tournament:
        return render_template('jury_evaluate.html', team_evaluations=[], current_user=jury, tournament=None, teams=[], message_key='no_active_tournament')

    sync_team_submissions(tournament)

    now = datetime.utcnow()
    finished_round = Round.query.filter(Round.tournament_id == tournament.id, Round.end_at <= now).first()
    submissions = Submission.query.join(Team, Submission.team_id == Team.id).filter(Team.tournament_id == tournament.id).all()
    team_level_submissions = Team.query.filter(
        Team.tournament_id == tournament.id,
        Team.repo_url.isnot(None),
        Team.repo_url != ''
    ).all()

    if not finished_round and not submissions and not team_level_submissions and tournament.status.lower() not in ('finished', 'completed', 'closed'):
        # no ended rounds and no submissions yet: evaluation period not started
        return render_template('jury_evaluate.html', team_evaluations=[], current_user=jury, tournament=tournament, teams=[], message_key='evaluation_not_started')

    # if tournament still in early phase but submits are already present, allow evaluation

    teams = Team.query.filter_by(tournament_id=tournament.id).all()

    # For each submission, check if evaluated by this jury
    team_evaluations = []
    for s in submissions:
        if s.team:  # Ensure team exists
            already = Evaluation.query.filter_by(submission_id=s.id, jury_id=jury.id).first()
            team_evaluations.append((s, already))

    return render_template('jury_evaluate.html', team_evaluations=team_evaluations, current_user=jury, tournament=tournament, teams=teams)

def jury_logout():
    session.pop('jury_id', None)
    flash('Logged out', 'info')
    return redirect('/')

# ---------------- JURY PART 2 ----------------
def jury_part2():
    if 'jury_id' not in session:
        return redirect('/jury/login')
    jury = User.query.get(session['jury_id'])
    if not jury or jury.role != 'jury':
        session.pop('jury_id', None)
        return redirect('/jury/login')
    
    return render_template('jury_part2.html')

# ---------------- PROFILE SWITCH ----------------
def profile_switch():
    if request.method == 'POST':
        email = request.form.get('switch_email', '').strip().lower()
        if not email:
            flash('Email is required', 'warning')
            return redirect(url_for('profile_switch'))
        target = User.query.filter_by(email=email).first()
        if not target:
            flash('User not found', 'danger')
            return redirect(url_for('profile_switch'))

        session['user_id'] = target.id
        flash(f'Switched profile to {target.email}', 'success')
        return redirect(url_for('user_profile', uid=target.id))

    # GET: render the switch form
    return render_template('profile_switch.html')

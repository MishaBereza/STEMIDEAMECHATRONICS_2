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

    from .models import Submission, Evaluation, Team, Tournament
    # use tournament 1 data (as requested)
    tournament = Tournament.query.get(1)
    teams = []
    if tournament:
        teams = Team.query.filter_by(tournament_id=tournament.id).all()

    # only include submissions for pending teams
    submissions = Submission.query.join(Team, Submission.team_id == Team.id).filter(Team.submission_status == 'Pending').all()

    unevaluated = []
    for s in submissions:
        already = Evaluation.query.filter_by(submission_id=s.id, jury_id=jury.id).first()
        if not already:
            unevaluated.append(s)

    return render_template('jury_evaluate.html', submissions=unevaluated, current_user=jury, tournament=tournament, teams=teams)

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
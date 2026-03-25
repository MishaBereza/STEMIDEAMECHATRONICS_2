from flask import render_template, request, redirect, url_for, flash
from .models import db, User, Tournament, Team, Round, Submission, Evaluation
from functools import wraps
from .app_helpers import admin_required

# ---------------- ADMIN DASHBOARD ----------------
def admin_dashboard():
    return render_template(
        'admin_dashboard.html',
        users_count=User.query.count(),
        tournaments_count=Tournament.query.count(),
        teams_count=Team.query.count(),
        submissions_count=Submission.query.count()
    )

# ---------------- ADMIN USERS ----------------
def admin_users():
    users = User.query.all()
    return render_template('admin_users.html', users=users, search="")

# DELETE USER
def admin_delete_user(uid):
    u = User.query.get_or_404(uid)
    # prevent removing admin accounts
    if u.role == 'admin':
        flash('Cannot delete admin user', 'warning')
        return redirect('/admin/users')

    # delete any teams where the user is captain, but keep the other users themselves
    captain_teams = Team.query.filter_by(captain_id=u.id).all()
    for team in captain_teams:
        try:
            members = team.members.all()
        except Exception:
            members = list(team.members)
        for member in members:
            try:
                team.members.remove(member)
            except Exception:
                pass

        for s in team.submissions:
            for ev in s.evaluations:
                db.session.delete(ev)
            db.session.delete(s)

        db.session.delete(team)

    # remove from any membership associations
    for team in list(u.teams):
        try:
            if hasattr(team.members, 'remove'):
                team.members.remove(u)
        except Exception:
            if u in team.members:
                team.members.remove(u)

    db.session.delete(u)
    db.session.commit()

    flash('User deleted', 'success')
    return redirect('/admin/users')

# CHANGE USER ROLE
def change_user_role(uid):
    u = User.query.get_or_404(uid)
    new_role = request.form.get('role')
    if new_role in ['team', 'jury', 'admin']:
        u.role = new_role
        db.session.commit()
        flash('User role updated', 'success')
    else:
        flash('Invalid role', 'warning')
    return redirect('/admin/users')

# ---------------- USER PROFILE ----------------
def user_profile(uid):
    u = User.query.get_or_404(uid)
    teams_captain = Team.query.filter_by(captain_id=u.id).all()
    # u.teams comes from backref, usually a list
    teams_member = list(u.teams)
    # collect tournaments the user participates in and separate past (finished) ones
    participating = []
    past = []
    seen = set()
    for team in teams_captain + teams_member:
        t = Tournament.query.get(team.tournament_id)
        if not t or t.id in seen:
            continue
        seen.add(t.id)
        # treat status 'Finished' as past; otherwise as current/participating
        if getattr(t, 'status', '').lower() == 'finished':
            past.append(t)
        else:
            participating.append(t)

    return render_template('profile.html', user=u, teams_captain=teams_captain, teams_member=teams_member,
                           participating=participating, past=past)

# ---------------- ADMIN TOURNAMENTS ----------------
def admin_tournaments():
    tournaments = Tournament.query.all()
    return render_template('admin_tournaments.html', tournaments=tournaments)

# backward-compatible redirect: some pages/linking use the plural path
def admin_tournaments_create_redirect():
    return redirect(url_for('create_tournament'))

# SHOW TEAMS FOR TOURNAMENT
def admin_tournament_teams(tid):
    t = Tournament.query.get_or_404(tid)
    teams = Team.query.filter_by(tournament_id=t.id).all()
    return render_template('admin_teams.html', tournament=t, teams=teams)

# DELETE TEAM
def admin_delete_team(teamid):
    team = Team.query.get_or_404(teamid)

    # remove member associations
    try:
        members = team.members.all()
    except Exception:
        # if not dynamic, it may be a list
        members = list(team.members)
    for u in members:
        try:
            team.members.remove(u)
        except Exception:
            pass

    # delete submissions and their evaluations
    for s in team.submissions:
        for ev in s.evaluations:
            db.session.delete(ev)
        db.session.delete(s)

    db.session.delete(team)
    db.session.commit()

    flash('Team deleted', 'success')
    return redirect(url_for('admin_tournament_teams', tid=team.tournament_id))

# ADMIN decision on pending submission
def admin_team_decide(teamid):
    team = Team.query.get_or_404(teamid)
    action = request.form.get('decision')
    if action == 'accept':
        team.submission_status = 'Accepted'
    elif action == 'reject':
        team.submission_status = 'Rejected'
    elif action == 'return':
        team.submission_status = 'Returned'
    from .models import db
    db.session.commit()
    flash(f"Team {action}", 'success')
    return redirect(url_for('admin_tournament_teams', tid=team.tournament_id))

def create_tournament():
    if request.method == 'POST':
        t = Tournament(
            name=request.form['name'],
            description=request.form.get('description',''),
            max_teams=int(request.form.get('max_teams')) if request.form.get('max_teams') else None,
            status="Draft"
        )

        from .models import db
        db.session.add(t)
        db.session.commit()

        flash('Tournament created', 'success')
        return redirect('/admin/tournaments')

    return render_template('admin_create_tournament.html')

# EDIT
def edit_tournament(tid):
    t = Tournament.query.get_or_404(tid)

    if request.method == 'POST':
        t.name = request.form['name']
        t.description = request.form.get('description','')
        t.max_teams = int(request.form.get('max_teams')) if request.form.get('max_teams') else None
        t.status = request.form.get('status', t.status)

        from .models import db
        db.session.commit()

        flash('Tournament updated', 'success')
        return redirect('/admin/tournaments')

    return render_template('admin_edit_tournament.html', tournament=t)

# DELETE
def delete_tournament(tid):
    t = Tournament.query.get_or_404(tid)

    for r in Round.query.filter_by(tournament_id=t.id):
        for s in r.submissions:
            for ev in s.evaluations:
                db.session.delete(ev)
            db.session.delete(s)
        db.session.delete(r)

    for team in Team.query.filter_by(tournament_id=t.id):
        # clear membership links first (dynamic relationship returns query)
        # `.members` is a dynamic AppenderQuery, so we iterate and remove users one by one
        for u in team.members.all():
            team.members.remove(u)
        for s in team.submissions:
            for ev in s.evaluations:
                db.session.delete(ev)
            db.session.delete(s)
        db.session.delete(team)

    db.session.delete(t)
    db.session.commit()

    flash('Tournament deleted', 'success')
    return redirect('/admin/tournaments')

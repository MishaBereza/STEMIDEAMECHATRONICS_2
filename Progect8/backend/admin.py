from flask import render_template, request, redirect, url_for, flash, session
from .models import db, User, Tournament, Team, Round, Submission
from .translations import get_text


def _t(key, **kwargs):
    return get_text(key, session.get('language', 'en'), **kwargs)


def admin_dashboard():
    return render_template(
        'admin_dashboard.html',
        users_count=User.query.count(),
        tournaments_count=Tournament.query.count(),
        teams_count=Team.query.count(),
        submissions_count=Submission.query.count()
    )


def admin_users():
    users = User.query.all()
    search = request.args.get('search', '').strip()
    if search:
        users = User.query.filter(User.email.ilike(f'%{search}%')).all()
    return render_template('admin_users.html', users=users, search=search)


def admin_delete_user(uid):
    u = User.query.get_or_404(uid)
    if u.role == 'admin':
        flash(_t('cannot_delete_admin_user'), 'warning')
        return redirect('/admin/users')

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

    for team in list(u.teams):
        try:
            if hasattr(team.members, 'remove'):
                team.members.remove(u)
        except Exception:
            if u in team.members:
                team.members.remove(u)

    db.session.delete(u)
    db.session.commit()
    flash(_t('user_deleted'), 'success')
    return redirect('/admin/users')


def change_user_role(uid):
    u = User.query.get_or_404(uid)
    new_role = request.form.get('role')
    if new_role in ['team', 'jury', 'admin']:
        u.role = new_role
        db.session.commit()
        flash(_t('user_role_updated'), 'success')
    else:
        flash(_t('invalid_role'), 'warning')
    return redirect('/admin/users')


def user_profile(uid):
    u = User.query.get_or_404(uid)
    teams_captain = Team.query.filter_by(captain_id=u.id).all()
    teams_member = list(u.teams)
    participating = []
    past = []
    seen = set()
    for team in teams_captain + teams_member:
        t = db.session.get(Tournament, team.tournament_id)
        if not t or t.id in seen:
            continue
        seen.add(t.id)
        if getattr(t, 'status', '').lower() == 'finished':
            past.append(t)
        else:
            participating.append(t)

    return render_template('profile.html', user=u, teams_captain=teams_captain, teams_member=teams_member, participating=participating, past=past)


def admin_tournaments():
    tournaments = Tournament.query.all()
    return render_template('admin_tournaments.html', tournaments=tournaments)


def admin_tournaments_create_redirect():
    return redirect(url_for('create_tournament'))


def admin_tournament_teams(tid):
    t = Tournament.query.get_or_404(tid)
    teams = Team.query.filter_by(tournament_id=t.id).all()
    return render_template('admin_teams.html', tournament=t, teams=teams)


def admin_delete_team(teamid):
    team = Team.query.get_or_404(teamid)

    try:
        members = team.members.all()
    except Exception:
        members = list(team.members)
    for u in members:
        try:
            team.members.remove(u)
        except Exception:
            pass

    for s in team.submissions:
        for ev in s.evaluations:
            db.session.delete(ev)
        db.session.delete(s)

    db.session.delete(team)
    db.session.commit()

    flash(_t('team_deleted'), 'success')
    return redirect(url_for('admin_tournament_teams', tid=team.tournament_id))


def admin_team_decide(teamid):
    team = Team.query.get_or_404(teamid)
    action = request.form.get('decision')
    if action == 'accept':
        team.submission_status = 'Accepted'
    elif action == 'reject':
        team.submission_status = 'Rejected'
    elif action == 'return':
        team.submission_status = 'Returned'
    db.session.commit()
    flash(_t(f'team_action_{action}'), 'success')
    return redirect(url_for('admin_tournament_teams', tid=team.tournament_id))


def create_tournament():
    if request.method == 'POST':
        t = Tournament(
            name=request.form['name'],
            description=request.form.get('description', ''),
            max_teams=int(request.form.get('max_teams')) if request.form.get('max_teams') else None,
            status='Draft'
        )
        db.session.add(t)
        db.session.commit()
        flash(_t('tournament_created'), 'success')
        return redirect('/admin/tournaments')

    return render_template('admin_create_tournament.html')


def edit_tournament(tid):
    t = Tournament.query.get_or_404(tid)

    if request.method == 'POST':
        t.name = request.form['name']
        t.description = request.form.get('description', '')
        t.max_teams = int(request.form.get('max_teams')) if request.form.get('max_teams') else None
        t.status = request.form.get('status', t.status)
        db.session.commit()
        flash(_t('tournament_updated'), 'success')
        return redirect('/admin/tournaments')

    return render_template('admin_edit_tournament.html', tournament=t)


def delete_tournament(tid):
    t = Tournament.query.get_or_404(tid)

    for r in Round.query.filter_by(tournament_id=t.id):
        for s in r.submissions:
            for ev in s.evaluations:
                db.session.delete(ev)
            db.session.delete(s)
        db.session.delete(r)

    for team in Team.query.filter_by(tournament_id=t.id):
        for u in team.members.all():
            team.members.remove(u)
        for s in team.submissions:
            for ev in s.evaluations:
                db.session.delete(ev)
            db.session.delete(s)
        db.session.delete(team)

    db.session.delete(t)
    db.session.commit()

    flash(_t('tournament_deleted'), 'success')
    return redirect('/admin/tournaments')

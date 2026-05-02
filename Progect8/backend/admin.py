from datetime import datetime

from flask import render_template, request, redirect, url_for, flash, session
from .models import db, User, Tournament, Team, Round, Submission, EvaluationCriteria
from .translations import get_text
from sqlalchemy import or_
from .auth import is_over_admin


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
    from .auth import OVER_ADMIN_EMAIL, LEGACY_OVER_ADMIN_EMAIL
    users = User.query.filter(User.email.notin_([OVER_ADMIN_EMAIL, LEGACY_OVER_ADMIN_EMAIL])).all()
    search = request.args.get('search', '').strip()
    if search:
        search_digits = ''.join(ch for ch in search if ch.isdigit())
        full_name = User.first_name + ' ' + User.last_name
        full_phone = User.phone_country_code + User.phone_number
        full_phone_spaced = User.phone_country_code + ' ' + User.phone_number
        filters = [
            User.email.ilike(f'%{search}%'),
            User.first_name.ilike(f'%{search}%'),
            User.last_name.ilike(f'%{search}%'),
            full_name.ilike(f'%{search}%'),
            User.phone_country_code.ilike(f'%{search}%'),
            full_phone.ilike(f'%{search}%'),
            full_phone_spaced.ilike(f'%{search}%')
        ]
        if search_digits:
            filters.append(User.phone_number.ilike(f'%{search_digits}%'))
        users = User.query.filter(User.email.notin_([OVER_ADMIN_EMAIL, LEGACY_OVER_ADMIN_EMAIL])).filter(or_(*filters)).all()
    return render_template('admin_users.html', users=users, search=search)


def admin_delete_user(uid):
    u = User.query.get_or_404(uid)
    if is_over_admin(u) or u.role == 'admin':
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
    from .app import trigger_update
    trigger_update()
    return redirect('/admin/users')


def change_user_role(uid):
    u = User.query.get_or_404(uid)
    if is_over_admin(u):
        flash(_t('cannot_delete_admin_user'), 'warning')
        return redirect('/admin/users')

    new_role = request.form.get('role')
    if new_role in ['team', 'jury', 'admin']:
        u.role = new_role
        db.session.commit()
        flash(_t('user_role_updated'), 'success')
        from .app import trigger_update
        trigger_update()
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


def admin_tournament_rounds(tid):
    t = Tournament.query.get_or_404(tid)
    rounds = Round.query.filter_by(tournament_id=t.id).order_by(Round.level.asc(), Round.id.asc()).all()
    return render_template('round_editor.html', tournament=t, rounds=rounds)


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
    from .app import trigger_update
    trigger_update()
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
    from .app import trigger_update
    trigger_update()
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

        first_round = Round(
            tournament_id=t.id,
            title='Round 1',
            description='',
            level=1,
            status='Draft'
        )
        db.session.add(first_round)
        db.session.commit()

        flash(_t('tournament_created'), 'success')
        from .app import trigger_update
        trigger_update()
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
        from .app import trigger_update
        trigger_update()
        return redirect('/admin/tournaments')

    return render_template('admin_edit_tournament.html', tournament=t)


def update_tournament_status(tid):
    t = Tournament.query.get_or_404(tid)
    new_status = request.form.get('status', '').strip()

    if new_status not in ['Draft', 'Registration', 'Running', 'Finished']:
        flash(_t('invalid_status'), 'warning')
        return redirect('/admin/tournaments')

    t.status = new_status
    db.session.commit()
    flash(_t('tournament_updated'), 'success')
    from .app import trigger_update
    trigger_update()
    return redirect('/admin/tournaments')


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

    # Delete evaluation criteria associated with the tournament
    for criteria in EvaluationCriteria.query.filter_by(tournament_id=t.id):
        db.session.delete(criteria)

    db.session.delete(t)
    db.session.commit()

    flash(_t('tournament_deleted'), 'success')
    from .app import trigger_update
    trigger_update()
    return redirect('/admin/tournaments')


def create_round(tid):
    tournament = Tournament.query.get_or_404(tid)

    if request.method == 'POST':
        title = request.form.get('title', '').strip()
        description = request.form.get('description', '').strip()
        level_raw = request.form.get('level', '').strip()

        if not title:
            flash(_t('round_title_required'), 'warning')
            return render_template('admin_create_round.html', tournament=tournament)

        level = int(level_raw) if level_raw else 1

        new_round = Round(
            title=title,
            description=description,
            level=level,
            tournament_id=tournament.id,
            status='Draft'
        )

        db.session.add(new_round)
        db.session.commit()

        flash(_t('round_created', title=title), 'success')
        from .app import trigger_update
        trigger_update()
        return redirect(url_for('admin_tournament_rounds', tid=tournament.id))

    return render_template('admin_create_round.html', tournament=tournament)


def admin_round_start(rid):
    round_item = Round.query.get_or_404(rid)

    if round_item.status == 'Draft':
        round_item.status = 'Active'
        round_item.start_at = datetime.utcnow()
        db.session.commit()
        flash(_t('round_started', level=round_item.level), 'success')
        from .app import trigger_update
        trigger_update()
    elif round_item.status == 'Active':
        flash(_t('round_already_active'), 'info')
    else:
        flash(_t('round_cannot_start', status=round_item.status), 'warning')

    return redirect(url_for('admin_tournament_rounds', tid=round_item.tournament_id))


def admin_round_close(rid):
    round_item = Round.query.get_or_404(rid)

    if round_item.status == 'Active':
        round_item.status = 'Closed'
        round_item.end_at = datetime.utcnow()
        db.session.commit()
        flash(_t('round_closed', level=round_item.level), 'success')
        from .app import trigger_update
        trigger_update()
    else:
        flash(_t('round_not_active'), 'warning')

    return redirect(url_for('admin_tournament_rounds', tid=round_item.tournament_id))


def delete_round(rid):
    round_item = Round.query.get_or_404(rid)
    tournament_id = round_item.tournament_id

    submissions = Submission.query.filter_by(round_id=round_item.id).all()
    for submission in submissions:
        for evaluation in submission.evaluations:
            db.session.delete(evaluation)
        db.session.delete(submission)

    db.session.delete(round_item)
    db.session.commit()

    flash(_t('round_deleted'), 'success')
    from .app import trigger_update
    trigger_update()
    return redirect(url_for('admin_tournament_rounds', tid=tournament_id))


def admin_tournament_evaluation_settings(tid):
    tournament = Tournament.query.get_or_404(tid)

    if request.method == 'POST':
        # Get criteria data from form
        criteria_ids = request.form.getlist('criteria_id[]')
        criteria_names = request.form.getlist('criteria_name[]')
        criteria_points = request.form.getlist('criteria_points[]')
        
        # Delete criteria that are marked for deletion
        delete_ids = request.form.getlist('delete_criteria[]')
        for cid in delete_ids:
            c = EvaluationCriteria.query.get(cid)
            if c and c.tournament_id == tournament.id:
                db.session.delete(c)
        
        # Update existing criteria
        for i, cid in enumerate(criteria_ids):
            if cid and cid.isdigit():
                c = EvaluationCriteria.query.get(int(cid))
                if c and c.tournament_id == tournament.id:
                    c.name = criteria_names[i].strip() if i < len(criteria_names) else ''
                    c.max_points = int(criteria_points[i]) if i < len(criteria_points) and criteria_points[i].isdigit() else 10
                    c.order = i
        
        # Add new criteria
        new_count = request.form.get('new_criteria_count', '0')
        if new_count.isdigit():
            for i in range(int(new_count)):
                name = request.form.get(f'new_criteria_name_{i}', '').strip()
                points_str = request.form.get(f'new_criteria_points_{i}', '10')
                points = int(points_str) if points_str.isdigit() else 10
                
                if name or i == 0:  # Allow empty name for first criterion
                    new_criteria = EvaluationCriteria(
                        tournament_id=tournament.id,
                        name=name,
                        max_points=points,
                        order=len(criteria_ids) + i
                    )
                    db.session.add(new_criteria)

        db.session.commit()
        flash(_t('evaluation_settings_saved'), 'success')
        return redirect(url_for('admin_tournament_evaluation_settings', tid=tournament.id))

    # Get existing criteria
    criteria = EvaluationCriteria.query.filter_by(tournament_id=tournament.id).order_by(EvaluationCriteria.order).all()
    return render_template('admin_evaluation_settings.html', tournament=tournament, criteria=criteria)

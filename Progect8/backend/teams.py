from flask import render_template, request, redirect, url_for, flash, session
from .models import Tournament, Team, User, Round, Submission, Evaluation, EvaluationCriteria, EvaluationScore, db
from .app_helpers import get_current_user
from .submissions import PASSING_SCORE
from .translations import get_text


def _t(key, **kwargs):
    return get_text(key, session.get('language', 'en'), **kwargs)


def register_team(tid):
    t = Tournament.query.get_or_404(tid)

    if request.method == 'POST':
        name = request.form['name'].strip()
        captain_email = request.form['captain_email'].strip().lower()
        member_emails = [e.strip().lower() for e in request.form.get('members', '').split(',') if e.strip()]

        captain = User.query.filter_by(email=captain_email).first()
        if not captain:
            flash(_t('captain_registered_required'), 'warning')
            return redirect(url_for('register_team', tid=tid))

        existing = Team.query.filter_by(tournament_id=t.id).all()
        for team in existing:
            if team.captain_id == captain.id:
                flash(_t('captain_already_leads'), 'warning')
                return redirect(url_for('register_team', tid=tid))
            for u in team.members:
                if u.email == captain_email or u.email in member_emails:
                    flash(_t('user_already_in_team'), 'warning')
                    return redirect(url_for('register_team', tid=tid))

        unique_emails = set(member_emails)
        if len(unique_emails) != len(member_emails):
            flash(_t('member_emails_unique'), 'warning')
            return redirect(url_for('register_team', tid=tid))

        members = []
        for email in member_emails:
            if email == captain_email:
                flash(_t('captain_not_member'), 'warning')
                return redirect(url_for('register_team', tid=tid))
            u = User.query.filter_by(email=email).first()
            if not u:
                flash(_t('member_not_registered', email=email), 'warning')
                return redirect(url_for('register_team', tid=tid))
            members.append(u)

        team = Team(name=name, captain_id=captain.id, tournament_id=t.id)
        db.session.add(team)
        db.session.commit()
        for u in members:
            team.members.append(u)
        db.session.commit()

        cur = get_current_user()
        if cur and cur.id == captain.id:
            session['team_id'] = team.id

        flash(_t('team_registered'), 'success')
        return redirect(url_for('tournament_page', tid=tid))

    return render_template('register_team.html', t_obj=t)


def team_page(teamid):
    team = Team.query.get_or_404(teamid)
    t = db.session.get(Tournament, team.tournament_id)
    user = get_current_user()
    is_finished = bool(t and t.status.lower() in ('finished', 'completed', 'closed'))

    is_member = False
    if user:
        if user.id == team.captain_id or user in team.members:
            is_member = True
        elif team.captain and team.captain.email.lower() == user.email.lower():
            is_member = True
        else:
            for m in team.members:
                if m.email.lower() == user.email.lower():
                    is_member = True
                    break
    can_edit = (is_member or session.get('admin'))
    can_edit_members = is_member or session.get('admin')
    can_submit = user and (user.id == team.captain_id or session.get('admin'))
    message = None

    def sync_team_submission_record():
        if not t or not team.repo_url:
            return
        latest_round = Round.query.filter_by(tournament_id=t.id).order_by(Round.level.desc(), Round.id.desc()).first()
        round_id = latest_round.id if latest_round else None
        submission_query = Submission.query.filter_by(team_id=team.id)
        if round_id is None:
            submission = submission_query.filter(Submission.round_id.is_(None)).first()
        else:
            submission = submission_query.filter_by(round_id=round_id).first()
        if not submission:
            submission = Submission(team_id=team.id, round_id=round_id)
            db.session.add(submission)

        submission.repo_url = team.repo_url
        submission.demo_url = team.live_url
        submission.description = team.comments

    if is_finished and team.submission_status in (None, '', 'None'):
        team.submission_status = 'Submitted'
        db.session.commit()

    if request.method == 'POST' and can_edit and t and not is_finished:
        repo = request.form.get('repo_url', '').strip()
        live = request.form.get('live_url', '').strip()
        members_emails = []
        for value in request.form.getlist('members'):
            members_emails.extend([email.strip().lower() for email in value.split(',') if email.strip()])
        if not repo:
            message = _t('github_repo_required')
        else:
            team.repo_url = repo
            team.live_url = live
            team.comments = request.form.get('comments', '')
            if can_edit_members:
                team.members = []
                for email in members_emails:
                    if email == team.captain.email.lower():
                        continue
                    u = User.query.filter_by(email=email).first()
                    if u and u.id != team.captain_id:
                        team.members.append(u)
            if request.form.get('action') == 'send':
                if can_submit:
                    team.submission_status = 'Pending'
                    from datetime import datetime
                    team.submitted_at = datetime.utcnow()
                    sync_team_submission_record()
                else:
                    flash(_t('only_captain_submit'), 'warning')
            db.session.commit()
            if request.form.get('action') == 'save':
                message = _t('saved')
            elif request.form.get('action') == 'send' and can_submit:
                message = _t('submitted')

    evaluation_rows = []
    if is_finished:
        submissions = Submission.query.filter_by(team_id=team.id).order_by(Submission.id.desc()).all()
        for submission in submissions:
            submission_evaluations = Evaluation.query.filter_by(submission_id=submission.id).order_by(Evaluation.id.asc()).all()
            for evaluation in submission_evaluations:
                jury = db.session.get(User, evaluation.jury_id)
                scores = [
                    evaluation.score1, evaluation.score2, evaluation.score3, evaluation.score4, evaluation.score5,
                    evaluation.score6, evaluation.score7, evaluation.score8, evaluation.score9, evaluation.score10
                ]
                evaluation_rows.append({
                    'submission': submission,
                    'jury': jury,
                    'evaluation': evaluation,
                    'scores': scores,
                    'total': evaluation.total(),
                })

    return render_template(
        'team.html',
        team=team,
        tournament=t,
        can_edit=can_edit,
        can_edit_members=can_edit_members,
        can_submit=can_submit,
        message=message,
        evaluation_rows=evaluation_rows,
        is_finished=is_finished
    )


def edit_team_members(teamid):
    team = Team.query.get_or_404(teamid)
    t = db.session.get(Tournament, team.tournament_id)
    user = get_current_user()
    is_member = False
    if user:
        if user.id == team.captain_id or user in team.members:
            is_member = True
        elif team.captain and team.captain.email.lower() == user.email.lower():
            is_member = True
        else:
            for m in team.members:
                if m.email.lower() == user.email.lower():
                    is_member = True
                    break
    can_edit_members = (is_member and t and t.status == 'Registration') or session.get('admin')
    if not can_edit_members:
        flash(_t('no_permission'), 'error')
        return redirect(url_for('team_page', teamid=teamid))

    message = None
    if request.method == 'POST' and can_edit_members:
        members_emails = [e.strip().lower() for e in request.form.getlist('members') if e.strip()]
        if request.form.get('action') == 'update_members':
            team.members = []
            for email in members_emails:
                if email == team.captain.email.lower():
                    continue
                u = User.query.filter_by(email=email).first()
                if u and u.id != team.captain_id:
                    team.members.append(u)
            db.session.commit()
            message = _t('members_updated')

    return render_template(
        'edit_team_members.html',
        team=team,
        tournament=t,
        message=message
    )


def team_round_results(teamid, rid):
    team = Team.query.get_or_404(teamid)
    round_item = Round.query.get_or_404(rid)

    if round_item.tournament_id != team.tournament_id:
        flash(_t('invalid_team_selection'), 'warning')
        return redirect(url_for('tournament_page', tid=team.tournament_id))

    tournament = db.session.get(Tournament, team.tournament_id)
    user = get_current_user()

    is_member = False
    if user:
        if user.id == team.captain_id or user in team.members:
            is_member = True
        elif team.captain and team.captain.email.lower() == user.email.lower():
            is_member = True
        else:
            for member in team.members:
                if member.email.lower() == user.email.lower():
                    is_member = True
                    break

    if not is_member and not session.get('admin'):
        flash(_t('not_allowed_submit_for_team'), 'warning')
        return redirect(url_for('tournament_page', tid=team.tournament_id))

    if round_item.status != 'Closed' and not session.get('admin'):
        flash(_t('round_not_active_for_submission'), 'warning')
        return redirect(url_for('tournament_page', tid=team.tournament_id))

    # Get evaluation criteria for this tournament
    criteria = EvaluationCriteria.query.filter_by(tournament_id=tournament.id).order_by(EvaluationCriteria.order).all()
    
    submissions = Submission.query.filter_by(team_id=team.id, round_id=round_item.id).order_by(Submission.id.desc()).all()
    evaluation_rows = []
    totals = []

    for submission in submissions:
        submission_evaluations = Evaluation.query.filter_by(submission_id=submission.id).order_by(Evaluation.id.asc()).all()
        for evaluation in submission_evaluations:
            jury = db.session.get(User, evaluation.jury_id)
            
            # Build criterion scores map
            criterion_scores = {}
            for score_entry in evaluation.criterion_scores:
                criterion_scores[score_entry.criteria_id] = score_entry.score
            
            # Create scores list matching criteria order
            scores = []
            for criterion in criteria:
                scores.append({
                    'criterion': criterion,
                    'score': criterion_scores.get(criterion.id)
                })
            
            total = evaluation.total()
            if total > 0:
                totals.append(total)
            evaluation_rows.append({
                'submission': submission,
                'jury': jury,
                'evaluation': evaluation,
                'scores': scores,
                'total': total,
            })

    average_score = sum(totals) / len(totals) if totals else 0

    return render_template(
        'team_round_results.html',
        team=team,
        tournament=tournament,
        round_item=round_item,
        evaluation_rows=evaluation_rows,
        average_score=average_score,
        criteria=criteria
    )

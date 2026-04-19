from datetime import datetime

from flask import render_template, request, redirect, url_for, flash, session
from .models import Round, Tournament, Team, Submission, User, Evaluation, EvaluationCriteria, EvaluationScore, db
from .app_helpers import get_current_user
from .translations import get_text

PASSING_SCORE = 50


def _t(key, **kwargs):
    return get_text(key, session.get('language', 'en'), **kwargs)


def _criterion_label(criterion):
    return criterion.name or f"{_t('criterion')} {criterion.id}"


def get_round_access_state(team, round_item):
    return True, None


def submit_solution(rid):
    r = Round.query.get_or_404(rid)
    t = db.session.get(Tournament, r.tournament_id)

    user = get_current_user()
    if session.get('admin'):
        teams = Team.query.filter_by(tournament_id=r.tournament_id).all()
    else:
        teams = []
        if user:
            for team in Team.query.filter_by(tournament_id=r.tournament_id).all():
                if team.captain_id == user.id or user in team.members:
                    allowed, _ = get_round_access_state(team, r)
                    if allowed:
                        teams.append(team)

    status_ok = t and t.status.lower() in ('submission', 'running') and r.status.lower() == 'active'

    if request.method == 'POST':
        if not t or t.status.lower() not in ('submission', 'running'):
            flash(_t('submissions_not_open'), 'warning')
            return redirect(url_for('tournament_page', tid=r.tournament_id))

        if r.status.lower() != 'active':
            flash(_t('round_not_active_for_submission'), 'warning')
            return redirect(url_for('tournament_page', tid=r.tournament_id))

        submitter_email = request.form.get('submitter_email', '').strip().lower()
        if not submitter_email and user:
            submitter_email = user.email.lower()

        submitter = User.query.filter_by(email=submitter_email).first() if submitter_email else None
        is_admin = session.get('admin')
        if not submitter and not is_admin:
            flash(_t('submitter_registered_required'), 'warning')
            return redirect(url_for('submit_solution', rid=rid))

        try:
            sel_team_id = int(request.form['team_id'])
        except (ValueError, TypeError):
            flash(_t('invalid_team_selection'), 'warning')
            return redirect(url_for('submit_solution', rid=rid))

        team_obj = db.session.get(Team, sel_team_id)
        if not team_obj or team_obj.tournament_id != r.tournament_id:
            flash(_t('invalid_team_selection'), 'warning')
            return redirect(url_for('submit_solution', rid=rid))

        allowed = False
        if is_admin:
            allowed = True
        elif team_obj.captain and submitter and team_obj.captain.email.lower() == submitter.email.lower():
            allowed = True
        else:
            for m in team_obj.members:
                if submitter and m.email.lower() == submitter.email.lower():
                    allowed = True
                    break

        if not allowed:
            flash(_t('not_allowed_submit_for_team'), 'warning')
            return redirect(url_for('submit_solution', rid=rid))

        if not is_admin:
            can_access_round, reason_key = get_round_access_state(team_obj, r)
            if not can_access_round:
                flash(_t(reason_key), 'warning')
                return redirect(url_for('tournament_page', tid=r.tournament_id))

        repo = request.form.get('repo_url', '').strip()
        if not repo:
            flash(_t('github_repo_required'), 'warning')
        else:
            submission = Submission.query.filter_by(
                team_id=sel_team_id,
                round_id=r.id
            ).order_by(Submission.id.asc()).first()

            if submission:
                for evaluation in list(submission.evaluations):
                    db.session.delete(evaluation)
            else:
                submission = Submission(
                    team_id=sel_team_id,
                    round_id=r.id,
                )
                db.session.add(submission)

            submission.repo_url = repo
            submission.demo_url = request.form.get('demo_url', '').strip()
            submission.description = request.form.get('description', '').strip()
            submission.submitted_at = datetime.utcnow()

            db.session.commit()
            flash(_t('submitted'), 'success')
            return redirect(url_for('tournament_page', tid=r.tournament_id))

    return render_template('submit.html', r=r, teams=teams, status_ok=status_ok, current_user=user)


def evaluate_submission(sid):
    if 'jury_id' not in session and 'admin' not in session:
        flash(_t('please_login_as_jury'), 'warning')
        return redirect('/jury/login')

    if 'jury_id' in session:
        jury = db.session.get(User, session['jury_id'])
        if not jury or jury.role not in ['jury', 'admin']:
            session.pop('jury_id', None)
            flash(_t('invalid_jury_session'), 'danger')
            return redirect('/jury/login')
    else:
        # Admin access
        jury = get_current_user()
        if not jury or jury.role != 'admin':
            session.pop('admin', None)
            flash(_t('invalid_admin_session'), 'danger')
            return redirect('/admin')

    s = Submission.query.get_or_404(sid)
    tournament = db.session.get(Tournament, s.round.tournament_id) if s.round else None
    criteria = []
    if tournament:
        criteria = EvaluationCriteria.query.filter_by(tournament_id=tournament.id).order_by(EvaluationCriteria.order).all()

    if not criteria:
        if request.method == 'POST':
            flash(_t('no_criteria_configured'), 'warning')
        return render_template('evaluate.html', s=s, criteria=criteria)

    if request.method == 'POST':
        comment = request.form.get('comment', '').strip()
        parsed_scores = {}
        for criterion in criteria:
            raw_value = request.form.get(f'criteria_score_{criterion.id}', '').strip()
            if not raw_value:
                flash(_t('score_required', field=_criterion_label(criterion)), 'warning')
                return render_template('evaluate.html', s=s, criteria=criteria)
            if len(raw_value) > 4:
                flash(_t('score_two_digits', field=_criterion_label(criterion)), 'warning')
                return render_template('evaluate.html', s=s, criteria=criteria)
            try:
                score_value = float(raw_value)
            except ValueError:
                flash(_t('score_number_range', field=_criterion_label(criterion)), 'warning')
                return render_template('evaluate.html', s=s, criteria=criteria)
            if score_value < 0 or score_value > criterion.max_points:
                flash(_t('score_between_range', field=f"{criterion.name or _t('criterion')} (0-{criterion.max_points})"), 'warning')
                return render_template('evaluate.html', s=s, criteria=criteria)
            parsed_scores[criterion.id] = score_value

        evaluation = Evaluation(
            submission_id=s.id,
            jury_id=jury.id,
            comment=comment
        )

        for criteria_id, score in parsed_scores.items():
            score_entry = EvaluationScore(
                criteria_id=criteria_id,
                score=score
            )
            evaluation.criterion_scores.append(score_entry)

        db.session.add(evaluation)
        try:
            db.session.commit()
        except Exception:
            db.session.rollback()
            flash(_t('failed_save_evaluation'), 'danger')
            return render_template('evaluate.html', s=s, criteria=criteria)
        flash(_t('evaluation_saved'), 'success')
        return redirect(url_for('jury_evaluate'))

    return render_template('evaluate.html', s=s, criteria=criteria)

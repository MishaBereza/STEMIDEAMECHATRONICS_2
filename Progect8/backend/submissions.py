from flask import render_template, request, redirect, url_for, flash, session
from .models import Round, Tournament, Team, Submission, User, Evaluation
from .app_helpers import get_current_user

# ---------------- SUBMISSION ----------------
def submit_solution(rid):
    r = Round.query.get_or_404(rid)
    t = Tournament.query.get(r.tournament_id)

    user = get_current_user()
    # limit team options to user's own teams (or all for admin)
    if session.get('admin'):
        teams = Team.query.filter_by(tournament_id=r.tournament_id).all()
    else:
        teams = []
        if user:
            for team in Team.query.filter_by(tournament_id=r.tournament_id).all():
                if team.captain_id == user.id or user in team.members:
                    teams.append(team)
    # verify tournament status allows submission (running also acceptable)
    status_ok = t and t.status.lower() in ('submission','running')

    if request.method == 'POST':
        # ensure status allows
        if not status_ok:
            flash('Submissions are not open', 'warning')
            return redirect(url_for('tournament_page', tid=r.tournament_id))

        # get submitter email from form or current user
        submitter_email = request.form.get('submitter_email','').strip().lower()
        if not submitter_email and user:
            submitter_email = user.email.lower()

        submitter = None
        if submitter_email:
            submitter = User.query.filter_by(email=submitter_email).first()

        # admin can bypass registration check
        is_admin = session.get('admin')
        if not submitter and not is_admin:
            flash('Submitter must be a registered user', 'warning')
            return redirect(url_for('submit_solution', rid=rid))

        try:
            sel_team_id = int(request.form['team_id'])
        except (ValueError, TypeError):
            flash('Invalid team selection', 'warning')
            return redirect(url_for('submit_solution', rid=rid))

        team_obj = Team.query.get(sel_team_id)
        if not team_obj or team_obj.tournament_id != r.tournament_id:
            flash('Invalid team selection', 'warning')
            return redirect(url_for('submit_solution', rid=rid))

        # verify submitter (by email) is captain or a member of the selected team (or admin)
        allowed = False
        if is_admin:
            allowed = True
        else:
            if team_obj.captain and submitter and team_obj.captain.email.lower() == submitter.email.lower():
                allowed = True
            else:
                for m in team_obj.members:
                    if submitter and m.email.lower() == submitter.email.lower():
                        allowed = True
                        break

        if not allowed:
            flash('You are not allowed to submit for that team', 'warning')
            return redirect(url_for('submit_solution', rid=rid))

        repo = request.form.get('repo_url','').strip()
        if not repo:
            flash('GitHub repo URL is required', 'warning')
            # fall through to re-render form with message
        else:
            submission = Submission(
                team_id=sel_team_id,
                round_id=r.id,
                repo_url=repo,
                demo_url=request.form.get('demo_url','').strip(),
                description=request.form.get('description','').strip()
            )
            from .models import db
            db.session.add(submission)
            db.session.commit()
            flash('Submitted', 'success')
            return redirect(url_for('tournament_page', tid=r.tournament_id))

    # GET or re-render after validation error
    # if user not eligible or no teams, show message in template
    return render_template('submit.html', r=r, teams=teams, status_ok=status_ok, current_user=user)

# ---------------- EVALUATE SUBMISSION ----------------
def evaluate_submission(sid):
    if 'jury_id' not in session:
        flash('Please login as jury first', 'warning')
        return redirect('/jury/login')
    
    jury = User.query.get(session['jury_id'])
    if not jury or jury.role != 'jury':
        session.pop('jury_id', None)
        flash('Invalid jury session', 'danger')
        return redirect('/jury/login')
    
    s = Submission.query.get_or_404(sid)
    
    if request.method == 'POST':
        raw_scores = {f'score{i}': request.form.get(f'score{i}', '').strip() for i in range(1, 11)}
        comment = request.form.get('comment', '').strip()
        parsed_scores = {}

        for field_name, raw_value in raw_scores.items():
            if not raw_value:
                flash(f'{field_name} is required', 'warning')
                return render_template('evaluate.html', s=s)
            try:
                score_value = float(raw_value)
            except ValueError:
                flash(f'{field_name} must be a number from 0 to 10', 'warning')
                return render_template('evaluate.html', s=s)
            if score_value < 0 or score_value > 10:
                flash(f'{field_name} must be between 0 and 10', 'warning')
                return render_template('evaluate.html', s=s)
            parsed_scores[field_name] = score_value
        
        evaluation = Evaluation(
            submission_id=s.id,
            jury_id=jury.id,
            score1=parsed_scores['score1'],
            score2=parsed_scores['score2'],
            score3=parsed_scores['score3'],
            score4=parsed_scores['score4'],
            score5=parsed_scores['score5'],
            score6=parsed_scores['score6'],
            score7=parsed_scores['score7'],
            score8=parsed_scores['score8'],
            score9=parsed_scores['score9'],
            score10=parsed_scores['score10'],
            comment=comment
        )
        from .models import db
        db.session.add(evaluation)
        db.session.commit()
        flash('Evaluation saved', 'success')
        return redirect('/jury/evaluate')
    
    return render_template('evaluate.html', s=s)

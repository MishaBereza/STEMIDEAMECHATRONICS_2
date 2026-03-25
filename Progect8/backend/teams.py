from flask import render_template, request, redirect, url_for, flash, session
from .models import Tournament, Team, User, Round, Submission
from .app_helpers import get_current_user

# ---------------- TEAM ----------------
def register_team(tid):
    t = Tournament.query.get_or_404(tid)

    if request.method == 'POST':
        name = request.form['name'].strip()
        captain_email = request.form['captain_email'].strip().lower()
        member_emails = [e.strip().lower() for e in request.form.get('members','').split(',') if e.strip()]

        # ensure captain exists
        captain = User.query.filter_by(email=captain_email).first()
        if not captain:
            flash('Captain must be a registered user', 'warning')
            return redirect(url_for('register_team', tid=tid))

        # prevent captain or any member from already being in another team in this tournament
        existing = Team.query.filter_by(tournament_id=t.id).all()
        for team in existing:
            if team.captain_id == captain.id:
                flash('Captain already leads another team in this tournament', 'warning')
                return redirect(url_for('register_team', tid=tid))
            for u in team.members:
                if u.email == captain_email or u.email in member_emails:
                    flash('One of the users is already in a team for this tournament', 'warning')
                    return redirect(url_for('register_team', tid=tid))

        # check member emails exist and no duplicates
        unique_emails = set(member_emails)
        if len(unique_emails) != len(member_emails):
            flash('Member emails must not repeat', 'warning')
            return redirect(url_for('register_team', tid=tid))

        members = []
        for email in member_emails:
            if email == captain_email:
                flash('Captain should not be listed as a member', 'warning')
                return redirect(url_for('register_team', tid=tid))
            u = User.query.filter_by(email=email).first()
            if not u:
                flash(f"Member {email} is not a registered user", 'warning')
                return redirect(url_for('register_team', tid=tid))
            members.append(u)

        team = Team(
            name=name,
            captain_id=captain.id,
            tournament_id=t.id
        )
        from .models import db
        db.session.add(team)
        db.session.commit()
        for u in members:
            team.members.append(u)
        db.session.commit()

        # remember team in session if current user
        cur = get_current_user()
        if cur and cur.id == captain.id:
            session['team_id'] = team.id

        flash('Team registered', 'success')
        return redirect(url_for('tournament_page', tid=tid))

    return render_template('register_team.html', t_obj=t)

# ---------------- TEAM VIEW & SUBMISSION ----------------
def team_page(teamid):
    team = Team.query.get_or_404(teamid)
    t = Tournament.query.get(team.tournament_id)
    user = get_current_user()

    # determine membership (captain + members) with email fallback
    is_member = False
    if user:
        if user.id == team.captain_id or user in team.members:
            is_member = True
        else:
            # also check by email in case relationship not populated
            if team.captain and team.captain.email.lower() == user.email.lower():
                is_member = True
            else:
                for m in team.members:
                    if m.email.lower() == user.email.lower():
                        is_member = True
                        break
    can_edit = (is_member or session.get('admin'))
    can_submit = user and (user.id == team.captain_id or session.get('admin'))
    message = None

    def sync_team_submission_record():
        """Mirror captain/team submission data into Submission for jury evaluation."""
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
            from .models import db
            db.session.add(submission)

        submission.repo_url = team.repo_url
        submission.demo_url = team.live_url
        submission.description = team.comments

    # if tournament has finished and team hasn't submitted yet (status blank/None), auto-mark submitted
    if t and t.status.lower() == 'finished' and team.submission_status in (None, '', 'None'):
        team.submission_status = 'Submitted'
        from .models import db
        db.session.commit()

    # allow save/submit until tournament is finished
    if request.method == 'POST' and can_edit and t and t.status.lower() != 'finished':
        repo = request.form.get('repo_url','').strip()
        live = request.form.get('live_url','').strip()
        members_emails = [e.strip().lower() for e in request.form.get('members','').split(',') if e.strip()]
        if not repo:
            message = 'GitHub repo URL is required'
        else:
            team.repo_url = repo
            team.live_url = live
            team.comments = request.form.get('comments','')
            # update members list if captain editing
            if can_submit:
                # rebuild membership from emails
                # first clear existing
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
                    flash('Only the captain can submit', 'warning')
            from .models import db
            db.session.commit()
            # message depends on whether action was save or attempt to send
            if request.form.get('action') == 'save':
                message = 'Saved'
            elif request.form.get('action') == 'send' and can_submit:
                message = 'Submitted'

    return render_template('team.html', team=team, tournament=t, can_edit=can_edit, can_submit=can_submit, message=message)

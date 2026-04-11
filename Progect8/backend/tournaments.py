from flask import render_template, flash, redirect, url_for, session
from sqlalchemy import or_

from .app_helpers import get_current_user
from .models import Team, Tournament
from .translations import get_text


def _t(key, **kwargs):
    return get_text(key, session.get('language', 'en'), **kwargs)


def index():
    tournaments = Tournament.query.all()
    registration_tournaments_count = Tournament.query.filter(
        or_(
            Tournament.status.ilike('%register%'),
            Tournament.status.ilike('%registration%')
        )
    ).count()
    return render_template(
        'index.html',
        tournaments=tournaments,
        registration_tournaments_count=registration_tournaments_count
    )


def tournament_page(tid):
    t = Tournament.query.get_or_404(tid)
    user = get_current_user()
    myteam = None
    if user:
        myteam = Team.query.filter_by(tournament_id=t.id, captain_id=user.id).first()
        if not myteam:
            for team in user.teams:
                if team.tournament_id == t.id:
                    myteam = team
                    break
    return render_template('tournament.html', tournament=t, myteam=myteam)


def leaderboard(tid):
    t = Tournament.query.get_or_404(tid)
    if t.status.lower() not in ['finished', 'completed', 'closed']:
        flash(_t('leaderboard_only_finished'), 'warning')
        return redirect(url_for('tournament_page', tid=tid))

    teams = Team.query.filter_by(tournament_id=t.id).all()
    team_scores = []

    for team in teams:
        evaluation_totals = []
        for submission in team.submissions:
            for evaluation in submission.evaluations:
                total = evaluation.total()
                if total > 0:
                    evaluation_totals.append(total)

        avg = sum(evaluation_totals) / len(evaluation_totals) if evaluation_totals else 0

        if not evaluation_totals:
            status_key = 'under_review'
        elif avg > 50:
            status_key = 'passed_next_round'
        else:
            status_key = 'not_passed'

        team_scores.append((team, avg, status_key))

    team_scores.sort(key=lambda item: item[1], reverse=True)
    return render_template('leaderboard.html', tournament=t, team_scores=team_scores)

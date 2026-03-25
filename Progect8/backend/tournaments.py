from flask import render_template, flash, redirect, url_for

from .app_helpers import get_current_user
from .models import Team, Tournament


def index():
    tournaments = Tournament.query.all()
    return render_template('index.html', tournaments=tournaments)


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
        flash('Leaderboard is only available for completed tournaments.', 'warning')
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

        if avg > 80:
            status_key = 'passed_next_round'
        elif avg < 50:
            status_key = 'not_passed'
        else:
            status_key = 'under_review'

        team_scores.append((team, avg, status_key))

    team_scores.sort(key=lambda item: item[1], reverse=True)
    return render_template('leaderboard.html', tournament=t, team_scores=team_scores)

from flask import render_template
from .models import Tournament, Team, Round, Submission, Evaluation
from .utils import calculate_average_score, generate_new_round
from .app_helpers import get_current_user

# ---------------- MAIN ----------------
def index():
    tournaments = Tournament.query.all()
    return render_template('index.html', tournaments=tournaments)

# ---------------- TOURNAMENT ----------------
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

# ---------------- LEADERBOARD ----------------
def leaderboard(tid):
    t = Tournament.query.get_or_404(tid)
    teams = Team.query.filter_by(tournament_id=t.id).all()

    team_scores = []
    all_scores = []
    for team in teams:
        scores = []
        for s in team.submissions:
            evs = [ev.total() for ev in s.evaluations]
            if evs:
                scores.append(sum(evs)/len(evs))
                all_scores.extend(evs)
        avg = calculate_average_score(scores)
        team_scores.append((team, avg))

    team_scores.sort(key=lambda x: x[1], reverse=True)

    # визначення поточного рівня з останнього раунду
    current_level = 1
    last_round = Round.query.filter_by(tournament_id=t.id).order_by(Round.level.desc()).first()
    if last_round:
        current_level = last_round.level

    # генерація рекомендації нового раунду (додаток В + С)
    next_round = generate_new_round(current_level, all_scores)

    return render_template('leaderboard.html', tournament=t, team_scores=team_scores, next_round=next_round)
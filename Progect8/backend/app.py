from flask import Flask, redirect, url_for, session, request
from .models import db
from .translations import get_text
from .app_helpers import get_current_user, inject_user, translation, admin_required
import os
from sqlalchemy import inspect, text

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///' + os.path.join(os.path.dirname(__file__), '..', 'data.db')
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY','dev-secret')

# Set template folder to the templates directory in the project root
app.template_folder = os.path.join(os.path.dirname(__file__), '..', 'templates')
app.static_folder = os.path.join(os.path.dirname(__file__), '..', 'static')

db.init_app(app)


def migrate_evaluation_table():
    inspector = inspect(db.engine)
    if 'evaluation' not in inspector.get_table_names():
        return

    existing_columns = {column['name'] for column in inspector.get_columns('evaluation')}
    required_columns = {
        'score1': 'ALTER TABLE evaluation ADD COLUMN score1 FLOAT',
        'score2': 'ALTER TABLE evaluation ADD COLUMN score2 FLOAT',
        'score3': 'ALTER TABLE evaluation ADD COLUMN score3 FLOAT',
        'score4': 'ALTER TABLE evaluation ADD COLUMN score4 FLOAT',
        'score5': 'ALTER TABLE evaluation ADD COLUMN score5 FLOAT',
        'score6': 'ALTER TABLE evaluation ADD COLUMN score6 FLOAT',
        'score7': 'ALTER TABLE evaluation ADD COLUMN score7 FLOAT',
        'score8': 'ALTER TABLE evaluation ADD COLUMN score8 FLOAT',
        'score9': 'ALTER TABLE evaluation ADD COLUMN score9 FLOAT',
        'score10': 'ALTER TABLE evaluation ADD COLUMN score10 FLOAT',
        'score_tech': 'ALTER TABLE evaluation ADD COLUMN score_tech FLOAT',
        'score_func': 'ALTER TABLE evaluation ADD COLUMN score_func FLOAT',
        'score_ui': 'ALTER TABLE evaluation ADD COLUMN score_ui FLOAT',
    }

    for column_name, ddl in required_columns.items():
        if column_name not in existing_columns:
            db.session.execute(text(ddl))

    legacy_score_columns = [f'score{i}' for i in range(1, 11)]
    if all(column in existing_columns for column in legacy_score_columns):
        score_sum = ' + '.join([f'COALESCE({column}, 0)' for column in legacy_score_columns])
        db.session.execute(text(
            f'UPDATE evaluation SET score_tech = {score_sum} '
            'WHERE score_tech IS NULL'
        ))

    db.session.commit()

with app.app_context():
    # Create tables during app setup because Flask 3.x removed before_first_request.
    db.create_all()
    migrate_evaluation_table()

@app.context_processor
def inject_user_processor():
    return inject_user()

@app.context_processor
def translation_processor():
    return translation()

@app.route('/set_language/<lang>')
def set_language(lang):
    from .translations import TRANSLATIONS
    if lang in TRANSLATIONS:
        session['language'] = lang
    return redirect(request.referrer or url_for('index'))

from .auth import register_user, user_login, user_logout, admin_panel, admin_logout, admin_change_password, jury_login, jury_evaluate, jury_logout, jury_part2, profile_switch
from .tournaments import index, tournament_page, leaderboard
from .teams import register_team, team_page, edit_team_members
from .submissions import submit_solution, evaluate_submission
from .admin import admin_dashboard, admin_users, admin_delete_user, user_profile, admin_tournaments, admin_tournaments_create_redirect, admin_tournament_teams, admin_delete_team, admin_team_decide, create_tournament, edit_tournament, delete_tournament, change_user_role

# Register routes
app.add_url_rule('/', 'index', index, methods=['GET'])
app.add_url_rule('/register', 'register_user', register_user, methods=['GET', 'POST'])
app.add_url_rule('/login', 'user_login', user_login, methods=['GET', 'POST'])
app.add_url_rule('/logout', 'user_logout', user_logout, methods=['GET'])
app.add_url_rule('/tournament/<int:tid>', 'tournament_page', tournament_page, methods=['GET'])
app.add_url_rule('/tournament/<int:tid>/register', 'register_team', register_team, methods=['GET', 'POST'])
app.add_url_rule('/round/<int:rid>/submit', 'submit_solution', submit_solution, methods=['GET', 'POST'])
app.add_url_rule('/leaderboard/<int:tid>', 'leaderboard', leaderboard, methods=['GET'])
app.add_url_rule('/admin', 'admin_panel', admin_panel, methods=['GET', 'POST'])
app.add_url_rule('/admin/logout', 'admin_logout', admin_logout, methods=['GET'])
app.add_url_rule('/team/<int:teamid>', 'team_page', team_page, methods=['GET', 'POST'])
app.add_url_rule('/edit_team_members/<int:teamid>', 'edit_team_members', edit_team_members, methods=['GET', 'POST'])
app.add_url_rule('/admin/dashboard', 'admin_dashboard', admin_dashboard, methods=['GET'])
app.add_url_rule('/admin/change_password', 'admin_change_password', admin_change_password, methods=['GET', 'POST'])
app.add_url_rule('/profile/switch', 'profile_switch', profile_switch, methods=['GET', 'POST'])
app.add_url_rule('/admin/users', 'admin_users', admin_users, methods=['GET'])
app.add_url_rule('/admin/user/<int:uid>/delete', 'admin_delete_user', admin_delete_user, methods=['POST'])
app.add_url_rule('/admin/user/<int:uid>/change-role', 'change_user_role', change_user_role, methods=['POST'])
app.add_url_rule('/user/<int:uid>', 'user_profile', user_profile, methods=['GET'])
app.add_url_rule('/admin/tournaments', 'admin_tournaments', admin_tournaments, methods=['GET'])
app.add_url_rule('/admin/tournaments/create', 'admin_tournaments_create_redirect', admin_tournaments_create_redirect, methods=['GET'])
app.add_url_rule('/admin/tournament/<int:tid>/teams', 'admin_tournament_teams', admin_tournament_teams, methods=['GET'])
app.add_url_rule('/admin/team/<int:teamid>/delete', 'admin_delete_team', admin_delete_team, methods=['POST'])
app.add_url_rule('/admin/team/<int:teamid>/decide', 'admin_team_decide', admin_team_decide, methods=['POST'])
app.add_url_rule('/admin/tournament/create', 'create_tournament', create_tournament, methods=['GET', 'POST'])
app.add_url_rule('/admin/tournament/<int:tid>/edit', 'edit_tournament', edit_tournament, methods=['GET', 'POST'])
app.add_url_rule('/admin/tournament/<int:tid>/delete', 'delete_tournament', delete_tournament, methods=['POST'])
app.add_url_rule('/jury/login', 'jury_login', jury_login, methods=['GET', 'POST'])
app.add_url_rule('/jury/evaluate', 'jury_evaluate', jury_evaluate, methods=['GET'])
app.add_url_rule('/evaluate/<int:sid>', 'evaluate_submission', evaluate_submission, methods=['GET', 'POST'])
app.add_url_rule('/jury/logout', 'jury_logout', jury_logout, methods=['GET'])
app.add_url_rule('/jury/part2', 'jury_part2', jury_part2, methods=['GET'])

# ---------------- RUN ----------------
if __name__ == '__main__':
    app.run(debug=True)

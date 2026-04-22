from flask import Flask, redirect, url_for, session, request
from .models import db
from .translations import get_text
from .app_helpers import get_current_user, inject_user, translation, admin_required
import os
from sqlalchemy import inspect, text

app = Flask(__name__)

# Database configuration - supports both Railway PostgreSQL and local SQLite
DATABASE_URL = os.environ.get('DATABASE_URL')
if DATABASE_URL:
    # Railway PostgreSQL
    if DATABASE_URL.startswith('postgres://'):
        DATABASE_URL = DATABASE_URL.replace('postgres://', 'postgresql://', 1)
    app.config['SQLALCHEMY_DATABASE_URI'] = DATABASE_URL
else:
    # Local SQLite
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


def migrate_user_table():
    inspector = inspect(db.engine)
    if 'user' not in inspector.get_table_names():
        return

    existing_columns = {column['name'] for column in inspector.get_columns('user')}
    if 'password_hash' not in existing_columns:
        db.session.execute(text("ALTER TABLE user ADD COLUMN password_hash VARCHAR(255) NOT NULL DEFAULT ''"))
    if 'phone_country_code' not in existing_columns:
        db.session.execute(text("ALTER TABLE user ADD COLUMN phone_country_code VARCHAR(10) NOT NULL DEFAULT '+380'"))
    if 'phone_number' not in existing_columns:
        db.session.execute(text("ALTER TABLE user ADD COLUMN phone_number VARCHAR(30) NOT NULL DEFAULT ''"))
    db.session.commit()

with app.app_context():
    # Create tables during app setup because Flask 3.x removed before_first_request.
    db.create_all()
    migrate_user_table()
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

from .auth import register_user, user_login, user_logout, admin_panel, admin_logout, admin_change_password, jury_login, jury_evaluate, jury_logout, jury_part2, profile_switch, user_change_password, user_change_phone
from .tournaments import index, tournament_page, leaderboard, get_team_details
from .teams import register_team, team_page, edit_team_members, team_round_results
from .submissions import submit_solution, evaluate_submission
from .admin import admin_round_start, admin_round_close, delete_round, admin_dashboard, admin_users, admin_delete_user, user_profile, admin_tournaments, admin_tournaments_create_redirect, admin_tournament_teams, admin_delete_team, admin_team_decide, create_tournament, edit_tournament, update_tournament_status, delete_tournament, change_user_role, admin_tournament_rounds, create_round, admin_tournament_evaluation_settings

# Register routes
app.add_url_rule('/', 'index', index, methods=['GET'])
app.add_url_rule('/register', 'register_user', register_user, methods=['GET', 'POST'])
app.add_url_rule('/login', 'user_login', user_login, methods=['GET', 'POST'])
app.add_url_rule('/logout', 'user_logout', user_logout, methods=['GET'])
app.add_url_rule('/tournament/<int:tid>', 'tournament_page', tournament_page, methods=['GET'])
app.add_url_rule('/tournament/<int:tid>/register', 'register_team', register_team, methods=['GET', 'POST'])
app.add_url_rule('/round/<int:rid>/submit', 'submit_solution', submit_solution, methods=['GET', 'POST'])
app.add_url_rule('/leaderboard/<int:tid>', 'leaderboard', leaderboard, methods=['GET'])
app.add_url_rule('/api/team/<int:team_id>/details', 'get_team_details', get_team_details, methods=['GET'])
app.add_url_rule('/admin', 'admin_panel', admin_panel, methods=['GET', 'POST'])
app.add_url_rule('/admin/logout', 'admin_logout', admin_logout, methods=['GET'])
app.add_url_rule('/team/<int:teamid>', 'team_page', team_page, methods=['GET', 'POST'])
app.add_url_rule('/team/<int:teamid>/round/<int:rid>/results', 'team_round_results', team_round_results, methods=['GET'])
app.add_url_rule('/edit_team_members/<int:teamid>', 'edit_team_members', edit_team_members, methods=['GET', 'POST'])
app.add_url_rule('/admin/dashboard', 'admin_dashboard', admin_dashboard, methods=['GET'])
app.add_url_rule('/admin/change_password', 'admin_change_password', admin_change_password, methods=['GET', 'POST'])
app.add_url_rule('/profile/switch', 'profile_switch', profile_switch, methods=['GET', 'POST'])
app.add_url_rule('/profile/change-password', 'user_change_password', user_change_password, methods=['GET', 'POST'])
app.add_url_rule('/profile/change-phone', 'user_change_phone', user_change_phone, methods=['GET', 'POST'])
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
app.add_url_rule('/admin/tournament/<int:tid>/status', 'update_tournament_status', update_tournament_status, methods=['POST'])
app.add_url_rule('/admin/tournament/<int:tid>/delete', 'delete_tournament', delete_tournament, methods=['POST'])
app.add_url_rule('/admin/tournament/<int:tid>/rounds', 'admin_tournament_rounds', admin_tournament_rounds, methods=['GET'])
app.add_url_rule('/admin/tournament/<int:tid>/rounds/new', 'create_round', create_round, methods=['GET', 'POST'])
app.add_url_rule('/admin/round/<int:rid>/start', 'admin_round_start', admin_round_start, methods=['POST'])
app.add_url_rule('/admin/round/<int:rid>/close', 'admin_round_close', admin_round_close, methods=['POST'])
app.add_url_rule('/admin/round/<int:rid>/delete', 'delete_round', delete_round, methods=['POST'])
app.add_url_rule('/admin/tournament/<int:tid>/evaluation-settings', 'admin_tournament_evaluation_settings', admin_tournament_evaluation_settings, methods=['GET', 'POST'])
app.add_url_rule('/jury/login', 'jury_login', jury_login, methods=['GET', 'POST'])
app.add_url_rule('/jury/evaluate', 'jury_evaluate', jury_evaluate, methods=['GET'])
app.add_url_rule('/evaluate/<int:sid>', 'evaluate_submission', evaluate_submission, methods=['GET', 'POST'])
app.add_url_rule('/jury/logout', 'jury_logout', jury_logout, methods=['GET'])
app.add_url_rule('/jury/part2', 'jury_part2', jury_part2, methods=['GET'])

# ---------------- RUN ----------------
if __name__ == '__main__':
    app.run(debug=True)

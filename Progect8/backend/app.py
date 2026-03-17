from flask import Flask, redirect, url_for, session, request
from .models import db
from .translations import get_text
from .app_helpers import get_current_user, inject_user, translation, admin_required
import os

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///' + os.path.join(os.path.dirname(__file__), '..', 'data.db')
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY','dev-secret')

# Set template folder to the templates directory in the project root
app.template_folder = os.path.join(os.path.dirname(__file__), '..', 'templates')
app.static_folder = os.path.join(os.path.dirname(__file__), '..', 'static')

db.init_app(app)

@app.before_first_request
def create_tables():
    # create tables if they don't exist; don't drop to preserve data on restart
    db.create_all()

@app.context_processor
def inject_user_processor():
    return inject_user()

@app.context_processor
def translation_processor():
    return translation()

@app.route('/set_language/<lang>')
def set_language(lang):
    from translations import TRANSLATIONS
    if lang in TRANSLATIONS:
        session['language'] = lang
    return redirect(request.referrer or url_for('index'))

from .auth import register_user, admin_panel, admin_logout, admin_change_password
from .tournaments import index, tournament_page, leaderboard
from .teams import register_team, team_page
from .submissions import submit_solution
from .admin import admin_dashboard, admin_users, admin_delete_user, user_profile, admin_tournaments, admin_tournaments_create_redirect, admin_tournament_teams, admin_delete_team, admin_team_decide, create_tournament, edit_tournament, delete_tournament

# Register routes
app.add_url_rule('/', 'index', index, methods=['GET'])
app.add_url_rule('/register', 'register_user', register_user, methods=['GET', 'POST'])
app.add_url_rule('/tournament/<int:tid>', 'tournament_page', tournament_page, methods=['GET'])
app.add_url_rule('/tournament/<int:tid>/register', 'register_team', register_team, methods=['GET', 'POST'])
app.add_url_rule('/round/<int:rid>/submit', 'submit_solution', submit_solution, methods=['GET', 'POST'])
app.add_url_rule('/leaderboard/<int:tid>', 'leaderboard', leaderboard, methods=['GET'])
app.add_url_rule('/admin', 'admin_panel', admin_panel, methods=['GET', 'POST'])
app.add_url_rule('/admin/logout', 'admin_logout', admin_logout, methods=['GET'])
app.add_url_rule('/team/<int:teamid>', 'team_page', team_page, methods=['GET', 'POST'])
app.add_url_rule('/admin/dashboard', 'admin_dashboard', admin_dashboard, methods=['GET'])
app.add_url_rule('/admin/change_password', 'admin_change_password', admin_change_password, methods=['GET', 'POST'])
app.add_url_rule('/admin/users', 'admin_users', admin_users, methods=['GET'])
app.add_url_rule('/admin/user/<int:uid>/delete', 'admin_delete_user', admin_delete_user, methods=['POST'])
app.add_url_rule('/user/<int:uid>', 'user_profile', user_profile, methods=['GET'])
app.add_url_rule('/admin/tournaments', 'admin_tournaments', admin_tournaments, methods=['GET'])
app.add_url_rule('/admin/tournaments/create', 'admin_tournaments_create_redirect', admin_tournaments_create_redirect, methods=['GET'])
app.add_url_rule('/admin/tournament/<int:tid>/teams', 'admin_tournament_teams', admin_tournament_teams, methods=['GET'])
app.add_url_rule('/admin/team/<int:teamid>/delete', 'admin_delete_team', admin_delete_team, methods=['POST'])
app.add_url_rule('/admin/team/<int:teamid>/decide', 'admin_team_decide', admin_team_decide, methods=['POST'])
app.add_url_rule('/admin/tournament/create', 'create_tournament', create_tournament, methods=['GET', 'POST'])
app.add_url_rule('/admin/tournament/<int:tid>/edit', 'edit_tournament', edit_tournament, methods=['GET', 'POST'])
app.add_url_rule('/admin/tournament/<int:tid>/delete', 'delete_tournament', delete_tournament, methods=['POST'])

# ---------------- RUN ----------------
if __name__ == '__main__':
    app.run(debug=True)
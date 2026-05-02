from flask import render_template, request, redirect, url_for, flash, session
from .models import db, User, Settings
from .translations import get_text
from .email_utils import get_verification_links, send_verification_email
from .app_helpers import get_current_user
import os
import re

OVER_ADMIN_EMAIL = 'over.admin@local'
LEGACY_OVER_ADMIN_EMAIL = '__super_admin__'
OVER_ADMIN_FIRST_NAME = 'Super'
OVER_ADMIN_LAST_NAME = 'Admin'


def _t(key, **kwargs):
    return get_text(key, session.get('language', 'en'), **kwargs)


PHONE_COUNTRY_CODES = ['+380', '+39', '+49', '+33', '+44', '+1', '+34', '+48']


def _normalize_phone_number(value, allow_plus=False):
    value = (value or '').strip()
    if allow_plus:
        digits = re.sub(r'\D+', '', value)
        return f"+{digits}" if value.startswith('+') and digits else digits
    return re.sub(r'\D+', '', value)


def _get_phone_form_data():
    raw_country_code = request.form.get('phone_country_code')
    raw_phone_number = request.form.get('phone_number', '').strip()
    if raw_country_code is None:
        return '', _normalize_phone_number(raw_phone_number, allow_plus=True)

    country_code = raw_country_code.strip()
    phone_number = _normalize_phone_number(raw_phone_number)
    if country_code not in PHONE_COUNTRY_CODES:
        country_code = ''
    return country_code, phone_number


def get_or_create_admin_password():
    setting = Settings.query.filter_by(key='admin_password').first()
    if setting:
        return setting.value
    default_pwd = 'admin123'
    setting = Settings(key='admin_password', value=default_pwd)
    db.session.add(setting)
    db.session.commit()
    return default_pwd


def load_admin_password():
    return get_or_create_admin_password()


def get_admin_user():
    """Get the primary admin user from the database"""
    return ensure_over_admin_user()


def is_over_admin(user):
    return bool(user and user.email in (OVER_ADMIN_EMAIL, LEGACY_OVER_ADMIN_EMAIL))


def _load_admin_key_value():
    key_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'admin_key.txt'))
    try:
        with open(key_path, encoding='utf-8') as key_file:
            return key_file.read().strip()
    except OSError:
        return ''


def ensure_over_admin_user():
    """Create the protected over-admin account once and return it."""
    user = User.query.filter(User.email.in_([OVER_ADMIN_EMAIL, LEGACY_OVER_ADMIN_EMAIL])).first()
    bootstrap_password = _load_admin_key_value() or os.urandom(32).hex()
    password_setting = Settings.query.filter_by(key='over_admin_password_initialized').first()
    if user:
        changed = False
        if user.email != OVER_ADMIN_EMAIL:
            user.email = OVER_ADMIN_EMAIL
            changed = True
        if user.role != 'admin':
            user.role = 'admin'
            changed = True
        if not user.is_verified:
            user.is_verified = True
            changed = True
        if user.verification_token:
            user.verification_token = None
            changed = True
        if user.first_name != OVER_ADMIN_FIRST_NAME:
            user.first_name = OVER_ADMIN_FIRST_NAME
            changed = True
        if user.last_name != OVER_ADMIN_LAST_NAME:
            user.last_name = OVER_ADMIN_LAST_NAME
            changed = True
        if user.phone_number != '000000000':
            user.phone_number = '000000000'
            changed = True
        if not password_setting:
            user.set_password(bootstrap_password)
            db.session.add(Settings(key='over_admin_password_initialized', value='1'))
            changed = True
        if changed:
            db.session.commit()
        return user

    user = User(
        first_name=OVER_ADMIN_FIRST_NAME,
        last_name=OVER_ADMIN_LAST_NAME,
        email=OVER_ADMIN_EMAIL,
        phone_country_code='+380',
        phone_number='000000000',
        role='admin',
        is_verified=True
    )
    user.set_password(bootstrap_password)
    db.session.add(user)
    if not password_setting:
        db.session.add(Settings(key='over_admin_password_initialized', value='1'))
    db.session.commit()
    return user


def login_over_admin():
    user = ensure_over_admin_user()
    session['admin'] = True
    session['admin_user_id'] = user.id
    session['user_id'] = user.id
    return user


def save_admin_password(new_password):
    setting = Settings.query.filter_by(key='admin_password').first()
    if setting:
        setting.value = new_password
    else:
        setting = Settings(key='admin_password', value=new_password)
        db.session.add(setting)
    db.session.commit()


def register_user():
    if request.method == 'POST':
        first_name = request.form['first_name'].strip()
        last_name = request.form['last_name'].strip()
        email = request.form['email'].strip().lower()
        age = request.form.get('age')
        dob = request.form.get('date_of_birth', '').strip()
        bio = request.form.get('bio', '')
        password = request.form.get('password', '').strip()
        confirm_password = request.form.get('confirm_password', '').strip()
        phone_country_code, phone_number = _get_phone_form_data()

        if dob:
            from datetime import datetime
            try:
                dob_date = datetime.strptime(dob, '%d/%m/%Y').date()
                today = datetime.utcnow().date()
                calculated_age = today.year - dob_date.year - ((today.month, today.day) < (dob_date.month, dob_date.day))
                age = str(max(calculated_age, 0))
            except ValueError:
                flash('Неправильна дата народження. Вкажіть у форматі DD/MM/YYYY.', 'warning')
                return redirect('/register')

        if not password:
            flash(_t('password_empty'), 'warning')
            return redirect('/register')
        if password != confirm_password:
            flash(_t('passwords_do_not_match'), 'warning')
            return redirect('/register')
        if not phone_number:
            flash(_t('phone_required'), 'warning')
            return redirect('/register')

        if User.query.filter_by(email=email).first():
            flash(_t('user_email_exists'), 'warning')
            return redirect('/register')
        if User.query.filter_by(first_name=first_name, last_name=last_name).first():
            flash(_t('user_name_exists'), 'warning')
            return redirect('/register')

        user = User(
            first_name=first_name,
            last_name=last_name,
            email=email,
            age=int(age) if age and age.isdigit() else None,
            bio=bio,
            phone_country_code=phone_country_code,
            phone_number=phone_number,
            role='team',
            is_verified=False
        )
        user.set_password(password)

        db.session.add(user)
        db.session.commit()

        # Keep the account pending until the user confirms the email link.
        email_sent = send_verification_email(user)

        if email_sent:
            flash(_t('verification_email_sent'), 'info')
        else:
            links = get_verification_links(user)
            # Debug info for email failure
            from flask import current_app
            mail_server = current_app.config.get('MAIL_SERVER', 'NOT SET')
            mail_username = current_app.config.get('MAIL_USERNAME', 'NOT SET')
            mail_password_set = bool(current_app.config.get('MAIL_PASSWORD'))
            mail_sender = current_app.config.get('MAIL_DEFAULT_SENDER', 'NOT SET')
            debug_info = f"Email could not be sent. Config: SERVER={mail_server}, USERNAME={mail_username}, PASSWORD_set={mail_password_set}, SENDER={mail_sender}"
            current_app.logger.error(debug_info)
            flash(
                f"Email could not be sent. Local verification link: {links['verify_url']}",
                'warning'
            )
        return redirect('/login')

    return render_template('register.html', phone_country_codes=PHONE_COUNTRY_CODES, default_phone_country_code='+380')


def user_login():
    if request.method == 'POST':
        email = request.form.get('email', '').strip().lower()
        password = request.form.get('password', '').strip()
        if not email:
            flash(_t('email_required'), 'warning')
            return redirect(url_for('user_login'))
        if not password:
            flash(_t('password_empty'), 'warning')
            return redirect(url_for('user_login'))

        user = User.query.filter_by(email=email).first()
        if not user:
            flash(_t('user_not_found'), 'danger')
            return redirect(url_for('user_login'))
        if is_over_admin(user):
            setting = Settings.query.filter_by(key='over_admin_enabled').first()
            if setting and setting.value.lower() in ('false', '0', 'no'):
                flash('Over admin account is disabled', 'danger')
                return redirect(url_for('user_login'))
        if not user.check_password(password):
            flash(_t('invalid_password'), 'danger')
            return redirect(url_for('user_login'))

        # Newly registered users keep a verification token until they confirm.
        # Legacy/test accounts without a token are allowed to log in.
        if user.verification_token and not user.is_verified:
            flash(_t('account_not_verified'), 'warning')
            return redirect(url_for('user_login'))

        # Store previous login time before updating
        from datetime import datetime
        user.last_login_at = datetime.now()
        db.session.commit()

        session['user_id'] = user.id
        flash(_t('logged_in_successfully'), 'success')
        return redirect(url_for('user_profile', uid=user.id))

    return render_template('user_login.html')


def user_logout():
    session.pop('user_id', None)
    flash(_t('logged_out'), 'info')
    return redirect(url_for('index'))


def admin_panel():
    current_user = get_current_user()
    if current_user and is_over_admin(current_user):
        login_over_admin()
        return redirect('/admin/dashboard')
    if request.method == 'POST':
        password = request.form.get('password', '').strip()
        if password == load_admin_password():
            login_over_admin()
            return redirect('/admin/dashboard')
        flash(_t('invalid_password'), 'danger')
    return render_template('admin_login.html')


def admin_logout():
    admin_user_id = session.get('admin_user_id')
    session.pop('admin', None)
    session.pop('admin_user_id', None)
    if admin_user_id and session.get('user_id') == admin_user_id:
        session.pop('user_id', None)
    return redirect('/')


def admin_change_password():
    if request.method == 'POST':
        new_password = request.form.get('new_password', '').strip()
        confirm = request.form.get('confirm_password', '').strip()
        if not new_password:
            flash(_t('password_empty'), 'warning')
        elif new_password != confirm:
            flash(_t('passwords_do_not_match'), 'warning')
        else:
            save_admin_password(new_password)
            flash(_t('admin_password_changed'), 'success')
            return redirect(url_for('admin_dashboard'))
    return render_template('admin_change_password.html')


def jury_login():
    if request.method == 'POST':
        email = request.form.get('email', '').strip().lower()
        user = User.query.filter_by(email=email, role='jury').first()
        if user:
            session['jury_id'] = user.id
            flash(_t('logged_in_as_jury'), 'success')
            return redirect('/jury/evaluate')
        flash(_t('invalid_jury_member'), 'danger')
    return render_template('jury_login.html')


def jury_evaluate():
    if 'jury_id' not in session and 'admin' not in session:
        return redirect('/jury/login')
    
    if 'jury_id' in session:
        jury = db.session.get(User, session['jury_id'])
        if not jury or jury.role not in ['jury', 'admin']:
            session.pop('jury_id', None)
            return redirect('/jury/login')
    else:
        # Admin access
        jury = get_admin_user()
        if not jury or jury.role != 'admin':
            session.pop('admin', None)
            return redirect('/admin')

    from sqlalchemy import or_
    from .models import Submission, Evaluation, Team, Tournament, Round
    from datetime import datetime

    def sync_team_submissions(tournaments):
        if not tournaments:
            return

        dirty = False
        tournament_ids = [t.id for t in tournaments]
        teams_with_work = Team.query.filter(
            Team.tournament_id.in_(tournament_ids),
            Team.repo_url.isnot(None),
            Team.repo_url != ''
        ).all()

        for team in teams_with_work:
            latest_round = Round.query.filter_by(tournament_id=team.tournament_id).order_by(Round.level.desc(), Round.id.desc()).first()
            round_id = latest_round.id if latest_round else None
            submission_query = Submission.query.filter_by(team_id=team.id)
            if round_id is None:
                submission = submission_query.filter(Submission.round_id.is_(None)).first()
            else:
                submission = submission_query.filter_by(round_id=round_id).first()
            if submission:
                changed = False
                if not submission.repo_url and team.repo_url:
                    submission.repo_url = team.repo_url
                    changed = True
                if not submission.demo_url and team.live_url:
                    submission.demo_url = team.live_url
                    changed = True
                if not submission.description and team.comments:
                    submission.description = team.comments
                    changed = True
                dirty = dirty or changed
                continue

            db.session.add(Submission(
                team_id=team.id,
                round_id=round_id,
                repo_url=team.repo_url,
                demo_url=team.live_url,
                description=team.comments
            ))
            dirty = True

        if dirty:
            db.session.commit()

    candidate_tournaments = Tournament.query.filter(
        or_(
            Tournament.status.ilike('%finished%'),
            Tournament.status.ilike('%completed%'),
            Tournament.status.ilike('%closed%'),
            Tournament.status.ilike('%running%'),
            Tournament.status.ilike('%submission%'),
            Tournament.status.ilike('%registration%'),
            Tournament.status.ilike('%draft%')
        )
    ).order_by(Tournament.id.desc()).all()

    tournament = None
    active_tournament_ids = []
    for ct in candidate_tournaments:
        has_submission = Submission.query.join(Team, Submission.team_id == Team.id).filter(Team.tournament_id == ct.id).first()
        has_team_submit = Team.query.filter(
            Team.tournament_id == ct.id,
            Team.repo_url.isnot(None),
            Team.repo_url != ''
        ).first()
        if has_submission or has_team_submit:
            active_tournament_ids.append(ct.id)
            if not tournament:
                tournament = ct

    if not tournament and candidate_tournaments:
        tournament = candidate_tournaments[0]

    if not candidate_tournaments:
        return render_template('jury_evaluate.html', team_evaluations=[], current_user=jury, tournament=None, teams=[], message_key='no_active_tournament')

    sync_team_submissions(candidate_tournaments)

    now = datetime.utcnow()
    finished_round = Round.query.filter(Round.tournament_id.in_([t.id for t in candidate_tournaments]), Round.end_at <= now).first()
    submissions = Submission.query.join(Team, Submission.team_id == Team.id).filter(Team.tournament_id.in_([t.id for t in candidate_tournaments])).all()
    team_level_submissions = Team.query.filter(
        Team.tournament_id.in_([t.id for t in candidate_tournaments]),
        Team.repo_url.isnot(None),
        Team.repo_url != ''
    ).all()

    if not finished_round and not submissions and not team_level_submissions and tournament.status.lower() not in ('finished', 'completed', 'closed'):
        return render_template('jury_evaluate.html', team_evaluations=[], current_user=jury, tournament=tournament, teams=[], message_key='evaluation_not_started')

    teams = Team.query.filter(Team.tournament_id.in_([t.id for t in candidate_tournaments])).all()
    pending_evaluations = []
    reviewed_evaluations = []
    for s in submissions:
        if s.team:
            already = Evaluation.query.filter_by(submission_id=s.id, jury_id=jury.id).first()
            if already:
                reviewed_evaluations.append((s, already))
            else:
                pending_evaluations.append((s, already))

    return render_template(
        'jury_evaluate.html',
        team_evaluations=pending_evaluations + reviewed_evaluations,
        pending_evaluations=pending_evaluations,
        reviewed_evaluations=reviewed_evaluations,
        current_user=jury,
        tournament=tournament,
        teams=teams
    )


def jury_logout():
    session.pop('jury_id', None)
    flash(_t('logged_out'), 'info')
    return redirect('/')


def jury_part2():
    if 'jury_id' not in session and 'admin' not in session:
        return redirect('/jury/login')
    
    if 'jury_id' in session:
        jury = db.session.get(User, session['jury_id'])
        if not jury or jury.role not in ['jury', 'admin']:
            session.pop('jury_id', None)
            return redirect('/jury/login')
    else:
        # Admin access
        jury = get_admin_user()
        if not jury or jury.role != 'admin':
            session.pop('admin', None)
            return redirect('/admin')
    return redirect('/jury/evaluate')


def profile_switch():
    if request.method == 'POST':
        email = request.form.get('switch_email', '').strip().lower()
        password = request.form.get('password', '').strip()
        if not email:
            flash(_t('email_required'), 'warning')
            return redirect(url_for('profile_switch'))
        if not password:
            flash(_t('password_empty'), 'warning')
            return redirect(url_for('profile_switch'))
        target = User.query.filter_by(email=email).first()
        if not target:
            flash(_t('user_not_found'), 'danger')
            return redirect(url_for('profile_switch'))
        if not target.check_password(password):
            flash(_t('invalid_password'), 'danger')
            return redirect(url_for('profile_switch'))

        session['user_id'] = target.id
        flash(_t('switched_profile_to', email=target.email), 'success')
        return redirect(url_for('user_profile', uid=target.id))

    return render_template('profile_switch.html')


def user_change_password():
    user_id = session.get('user_id')
    if not user_id:
        flash(_t('please_login_first'), 'warning')
        return redirect(url_for('user_login'))

    user = db.session.get(User, user_id)
    if not user:
        session.pop('user_id', None)
        flash(_t('user_not_found'), 'danger')
        return redirect(url_for('user_login'))

    if is_over_admin(user):
        flash('Ця дія недоступна для over admin.', 'warning')
        return redirect(url_for('user_profile', uid=user.id))

    if request.method == 'POST':
        current_password = request.form.get('current_password', '').strip()
        new_password = request.form.get('new_password', '').strip()
        confirm_password = request.form.get('confirm_password', '').strip()

        if not current_password:
            flash(_t('current_password_required'), 'warning')
            return redirect(url_for('user_change_password'))
        if not user.check_password(current_password):
            flash(_t('invalid_password'), 'danger')
            return redirect(url_for('user_change_password'))
        if not new_password:
            flash(_t('password_empty'), 'warning')
            return redirect(url_for('user_change_password'))
        if new_password != confirm_password:
            flash(_t('passwords_do_not_match'), 'warning')
            return redirect(url_for('user_change_password'))

        user.set_password(new_password)
        db.session.commit()
        flash(_t('user_password_changed'), 'success')
        return redirect(url_for('user_profile', uid=user.id))

    return render_template('change_user_password.html')


def user_edit_profile():
    user_id = session.get('user_id')
    if not user_id:
        flash(_t('please_login_first'), 'warning')
        return redirect(url_for('user_login'))

    user = db.session.get(User, user_id)
    if not user:
        session.pop('user_id', None)
        flash(_t('user_not_found'), 'danger')
        return redirect(url_for('user_login'))

    if is_over_admin(user):
        flash('Ця дія недоступна для over admin.', 'warning')
        return redirect(url_for('user_profile', uid=user.id))

    if request.method == 'POST':
        current_password = request.form.get('current_password', '').strip()
        first_name = request.form.get('first_name', '').strip()
        last_name = request.form.get('last_name', '').strip()
        age = request.form.get('age', '').strip()

        if not current_password:
            flash(_t('current_password_required'), 'warning')
            return redirect(url_for('user_edit_profile'))
        if not user.check_password(current_password):
            flash(_t('invalid_password'), 'danger')
            return redirect(url_for('user_edit_profile'))
        if not first_name or not last_name:
            flash('Ім’я та прізвище обов’язкові.', 'warning')
            return redirect(url_for('user_edit_profile'))

        user.first_name = first_name
        user.last_name = last_name
        user.age = int(age) if age.isdigit() else None
        db.session.commit()
        flash('Профіль успішно оновлено.', 'success')
        return redirect(url_for('user_profile', uid=user.id))

    return render_template('edit_profile.html', user=user)


def user_change_phone():
    user_id = session.get('user_id')
    if not user_id:
        flash(_t('please_login_first'), 'warning')
        return redirect(url_for('user_login'))

    user = db.session.get(User, user_id)
    if not user:
        session.pop('user_id', None)
        flash(_t('user_not_found'), 'danger')
        return redirect(url_for('user_login'))

    if is_over_admin(user):
        flash('Ця дія недоступна для over admin.', 'warning')
        return redirect(url_for('user_profile', uid=user.id))

    if request.method == 'POST':
        current_password = request.form.get('current_password', '').strip()
        phone_country_code, phone_number = _get_phone_form_data()

        if not current_password:
            flash(_t('current_password_required'), 'warning')
            return redirect(url_for('user_change_phone'))
        if not user.check_password(current_password):
            flash(_t('invalid_password'), 'danger')
            return redirect(url_for('user_change_phone'))
        if not phone_number:
            flash(_t('phone_required'), 'warning')
            return redirect(url_for('user_change_phone'))

        user.phone_country_code = phone_country_code
        user.phone_number = phone_number
        db.session.commit()
        flash(_t('phone_updated_successfully'), 'success')
        return redirect(url_for('user_profile', uid=user.id))

    return render_template(
        'change_user_phone.html',
        current_phone_number=user.phone_display or ''
    )

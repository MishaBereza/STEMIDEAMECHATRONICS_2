from flask import session, flash, redirect, url_for
from .models import User
from .translations import get_text, TRANSLATIONS
from functools import wraps

# ---------------- HELPERS ----------------
def get_current_user():
    uid = session.get('user_id')
    if uid:
        return User.query.get(uid)
    return None

def inject_user():
    # expose helper to templates
    return {'get_current_user': get_current_user}

def translation():
    lang = session.get('language', 'en')

    def t(key):
        return get_text(key, lang)

    return {
        't': t,
        'lang': lang,
        'supported_languages': list(TRANSLATIONS.keys())
    }

# ---------------- ADMIN HELPERS ----------------
def admin_required(fn):
    @wraps(fn)
    def wrapper(*args, **kwargs):
        if not session.get('admin'):
            flash('Please login as admin', 'warning')
            return redirect(url_for('admin_panel'))
        return fn(*args, **kwargs)
    return wrapper
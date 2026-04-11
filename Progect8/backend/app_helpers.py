from flask import session, flash, redirect, url_for
from .models import User, db
from .translations import get_text, TRANSLATIONS
from functools import wraps


def get_current_user():
    uid = session.get('user_id')
    if uid:
        return db.session.get(User, uid)
    return None


def inject_user():
    return {'get_current_user': get_current_user}


def translation():
    lang = session.get('language', 'en')

    def t(key, **kwargs):
        return get_text(key, lang, **kwargs)

    return {
        't': t,
        'lang': lang,
        'supported_languages': list(TRANSLATIONS.keys())
    }


def admin_required(fn):
    @wraps(fn)
    def wrapper(*args, **kwargs):
        if not session.get('admin'):
            flash(get_text('please_login_as_admin', session.get('language', 'en')), 'warning')
            return redirect(url_for('admin_panel'))
        return fn(*args, **kwargs)
    return wrapper

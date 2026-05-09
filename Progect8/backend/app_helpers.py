from flask import session, flash, redirect, url_for
from .models import User, db
from .translations import get_text, TRANSLATIONS
from functools import wraps
from markupsafe import Markup, escape


def get_current_user():
    uid = session.get('user_id')
    if uid:
        return db.session.get(User, uid)
    return None


def inject_user():
    return {'get_current_user': get_current_user}


def translation():
    lang = session.get('language', 'en')
    value_key_map = {
        'draft': 'draft',
        'active': 'active',
        'closed': 'closed',
        'registration': 'registration',
        'submission': 'submission',
        'running': 'running',
        'finished': 'finished',
        'pending': 'pending',
        'accepted': 'accepted',
        'rejected': 'rejected',
        'returned': 'returned',
        'submitted': 'submitted',
        'admin': 'admin_short',
        'jury': 'jury_short',
        'team': 'team',
    }

    def t(key, **kwargs):
        return get_text(key, lang, **kwargs)

    def translate_value(value):
        if value is None:
            return value
        key = value_key_map.get(str(value).strip().lower())
        return get_text(key, lang) if key else value

    def wrap_text(value, chunk_size):
        if value is None:
            return ''

        text = str(value)
        if not text or chunk_size <= 0:
            return escape(text)

        chunks = [escape(text[i:i + chunk_size]) for i in range(0, len(text), chunk_size)]
        return Markup('<br>').join(chunks)

    return {
        't': t,
        'translate_value': translate_value,
        'wrap_text': wrap_text,
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

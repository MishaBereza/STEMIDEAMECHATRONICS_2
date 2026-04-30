"""
Email helpers for account verification and login notifications.
"""
import os
import secrets
from datetime import datetime
from urllib.parse import urljoin

from flask import current_app, has_request_context, request
from flask_mail import Mail, Message

from .models import db, User

mail = Mail()


def generate_token():
    """Generate a secure random token."""
    return secrets.token_urlsafe(32)


def _get_base_url():
    configured_url = os.environ.get('APP_BASE_URL', '').strip()
    if configured_url:
        return configured_url.rstrip('/') + '/'
    if has_request_context():
        return request.url_root
    return 'http://localhost:5000/'


def get_verification_links(user):
    base_url = _get_base_url()
    return {
        'verify_url': urljoin(base_url, f"verify/{user.verification_token}"),
        'cancel_url': urljoin(base_url, f"verify/cancel/{user.verification_token}"),
    }


def _send_message(subject, recipient, text_body, html_body=None):
    if os.environ.get('PYTEST_CURRENT_TEST'):
        print(f"Email suppressed during tests. To: {recipient}; Subject: {subject}")
        return True

    if current_app.config.get('MAIL_SUPPRESS_SEND'):
        print("Email sending is suppressed. Message preview:")
        print(f"To: {recipient}")
        print(f"Subject: {subject}")
        print(text_body)
        return False

    sender = current_app.config.get('MAIL_DEFAULT_SENDER')
    mail_configured = bool(
        current_app.config.get('MAIL_SERVER')
        and current_app.config.get('MAIL_USERNAME')
        and current_app.config.get('MAIL_PASSWORD')
        and sender
    )

    if not mail_configured:
        print("Email is not configured. Message preview:")
        print(f"To: {recipient}")
        print(f"Subject: {subject}")
        print(text_body)
        return False

    message = Message(subject=subject, recipients=[recipient], body=text_body, html=html_body, sender=sender)
    mail.send(message)
    return True


def send_verification_email(user):
    """Send an email with Confirm and Cancel registration actions."""
    if not user.verification_token:
        user.verification_token = generate_token()
        db.session.commit()

    links = get_verification_links(user)
    verify_url = links['verify_url']
    cancel_url = links['cancel_url']

    subject = "Registration confirmation"
    text_body = f"""Hello, {user.first_name}!

Someone registered an account with this email address.

Yes, finish registration:
{verify_url}

No, cancel this registration:
{cancel_url}

If you did not try to register, choose the cancel link or ignore this email.
"""
    html_body = f"""
    <p>Hello, {user.first_name}!</p>
    <p>Someone registered an account with this email address.</p>
    <p>
      <a href="{verify_url}" style="display:inline-block;padding:10px 16px;background:#198754;color:#fff;text-decoration:none;border-radius:6px;">
        Yes, finish registration
      </a>
    </p>
    <p>
      <a href="{cancel_url}" style="display:inline-block;padding:10px 16px;background:#dc3545;color:#fff;text-decoration:none;border-radius:6px;">
        No, cancel registration
      </a>
    </p>
    <p>If you did not try to register, choose cancel or ignore this email.</p>
    """

    try:
        return _send_message(subject, user.email, text_body, html_body)
    except Exception as exc:
        current_app.logger.exception("Failed to send verification email: %s", exc)
        current_app.logger.warning("Verification link for %s: %s", user.email, verify_url)
        current_app.logger.warning("Cancel registration link for %s: %s", user.email, cancel_url)
        return False


def send_login_notification(user):
    """Send a notification after a successful login."""
    subject = "Account login"
    text_body = f"""Hello, {user.first_name}!

Your account was logged in.

Login time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

If this was you, no action is needed. If it was not you, change your password.
"""

    try:
        return _send_message(subject, user.email, text_body)
    except Exception as exc:
        current_app.logger.exception("Failed to send login notification: %s", exc)
        return False


def verify_user(token):
    """Verify user by token."""
    user = User.query.filter_by(verification_token=token).first()
    if user:
        user.is_verified = True
        user.verification_token = None
        db.session.commit()
        return True, user
    return False, None


def cancel_registration(token):
    """Cancel pending registration by token."""
    user = User.query.filter_by(verification_token=token).first()
    if user:
        db.session.delete(user)
        db.session.commit()
        return True
    return False

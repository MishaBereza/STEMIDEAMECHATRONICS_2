"""
Email helpers for account verification and login notifications.
"""
import os
import secrets
import json
from concurrent.futures import ThreadPoolExecutor, TimeoutError
from datetime import datetime
from urllib.parse import urljoin
from urllib.request import Request, urlopen

from flask import current_app, has_request_context, request
from flask_mail import Mail, Message

from .models import db, User

mail = Mail()
_mail_executor = ThreadPoolExecutor(max_workers=2)


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

    if _should_use_sendgrid_api():
        return _send_sendgrid_api(subject, recipient, text_body, html_body, sender)

    message = Message(subject=subject, recipients=[recipient], body=text_body, html=html_body, sender=sender)
    app = current_app._get_current_object()
    timeout = current_app.config.get('MAIL_TIMEOUT') or 10

    def _send_with_context():
        with app.app_context():
            mail.send(message)

    future = _mail_executor.submit(_send_with_context)
    try:
        future.result(timeout=timeout)
    except TimeoutError:
        current_app.logger.error("Email sending timed out after %s seconds. To: %s; Subject: %s", timeout, recipient, subject)
        return False
    return True


def _should_use_sendgrid_api():
    mail_server = current_app.config.get('MAIL_SERVER', '')
    mail_password = current_app.config.get('MAIL_PASSWORD', '')
    is_sendgrid = mail_server == 'smtp.sendgrid.net' and mail_password.startswith('SG.')
    current_app.logger.info(f"Email config: SERVER='{mail_server}', has_password={bool(mail_password)}, password_starts_SG={mail_password.startswith('SG.') if mail_password else False}, use_sendgrid_api={is_sendgrid}")
    return is_sendgrid


def _send_sendgrid_api(subject, recipient, text_body, html_body, sender):
    timeout = current_app.config.get('MAIL_TIMEOUT') or 10
    current_app.logger.info(f"Sending via SendGrid API to {recipient}, subject: {subject}")
    
    payload = {
        'personalizations': [{'to': [{'email': recipient}]}],
        'from': {'email': sender},
        'subject': subject,
        'content': [{'type': 'text/plain', 'value': text_body}],
    }
    if html_body:
        payload['content'].append({'type': 'text/html', 'value': html_body})

    request = Request(
        'https://api.sendgrid.com/v3/mail/send',
        data=json.dumps(payload).encode('utf-8'),
        headers={
            'Authorization': f"Bearer {current_app.config['MAIL_PASSWORD']}",
            'Content-Type': 'application/json',
        },
        method='POST',
    )

    try:
        with urlopen(request, timeout=timeout) as response:
            current_app.logger.info(f"SendGrid response status: {response.status}")
            if response.status not in (200, 202):
                current_app.logger.error("SendGrid API returned status %s for %s", response.status, recipient)
                return False
    except Exception as e:
        current_app.logger.error(f"SendGrid API error: {e}")
        raise
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

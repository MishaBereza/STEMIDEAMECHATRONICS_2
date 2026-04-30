import os
import sys

ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

from backend.app import app, db
from backend.auth import OVER_ADMIN_EMAIL, ensure_over_admin_user, is_over_admin
from backend.models import User


def clear_database():
    with app.app_context():
        db.drop_all()
        db.create_all()
        over_admin = ensure_over_admin_user()
        print("Database cleared successfully.")
        print(f"Over-admin recreated: {over_admin.email}")


def ensure_over_admin():
    with app.app_context():
        ensure_over_admin_user()
        print("Super-admin is ready.")
        print("Open /admin to switch this browser session automatically.")


def list_admins():
    with app.app_context():
        users = User.query.filter(User.role.in_(['jury', 'admin'])).order_by(User.role, User.email).all()
        if not users:
            print("No jury/admin users found.")
            return
        for user in users:
            marker = " [SUPER-ADMIN]" if is_over_admin(user) else ""
            print(f"{user.email}: {user.first_name} {user.last_name} ({user.role}){marker}")


COMMANDS = {
    'clear-database': clear_database,
    'ensure-over-admin': ensure_over_admin,
    'list-admins': list_admins,
}


if __name__ == '__main__':
    command = sys.argv[1] if len(sys.argv) > 1 else ''
    handler = COMMANDS.get(command)
    if not handler:
        print("Usage: python scripts/admin_tools.py <clear-database|ensure-over-admin|list-admins>")
        sys.exit(1)
    handler()

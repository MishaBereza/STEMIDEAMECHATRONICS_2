from flask import render_template, request, redirect, url_for, flash, session
from .models import db, User
import os

ADMIN_PASSWORD_FILE = os.path.join(os.path.dirname(__file__), '..', 'admin_password.txt')

def get_or_create_admin_password():
    if os.path.exists(ADMIN_PASSWORD_FILE):
        with open(ADMIN_PASSWORD_FILE, 'r', encoding='utf-8') as f:
            return f.read().strip()
    default_pwd = 'admin123'
    with open(ADMIN_PASSWORD_FILE, 'w', encoding='utf-8') as f:
        f.write(default_pwd)
    return default_pwd

def load_admin_password():
    return get_or_create_admin_password()

def save_admin_password(new_password):
    with open(ADMIN_PASSWORD_FILE, 'w', encoding='utf-8') as f:
        f.write(new_password)

# ---------------- USER REGISTRATION ----------------
def register_user():
    if request.method == 'POST':
        first_name = request.form['first_name'].strip()
        last_name = request.form['last_name'].strip()
        email = request.form['email'].strip().lower()
        age = request.form.get('age')
        bio = request.form.get('bio','')

        # email unique check
        if User.query.filter_by(email=email).first():
            flash('User with that email already exists', 'warning')
            return redirect('/register')
        # combination of first+last name should also be unique (nicknames)
        if User.query.filter_by(first_name=first_name, last_name=last_name).first():
            flash('User with that name already exists', 'warning')
            return redirect('/register')

        user = User(
            first_name=first_name,
            last_name=last_name,
            email=email,
            age=int(age) if age else None,
            bio=bio,
            role='team'
        )

        db.session.add(user)
        db.session.commit()

        # set session so we can remember the user
        session['user_id'] = user.id

        flash('Registered successfully', 'success')
        return redirect('/')

    return render_template('register.html')

# ---------------- ADMIN LOGIN ----------------
def admin_panel():
    if request.method == 'POST':
        current_password = load_admin_password()
        if request.form.get('password') == current_password:
            session['admin'] = True
            return redirect('/admin/dashboard')
        else:
            flash('Невірний пароль', 'danger')
    return render_template('admin_login.html')

def admin_logout():
    session.pop('admin', None)
    return redirect('/')

def admin_change_password():
    if request.method == 'POST':
        new_password = request.form.get('new_password','').strip()
        confirm = request.form.get('confirm_password','').strip()
        if not new_password:
            flash('Password cannot be empty', 'warning')
        elif new_password != confirm:
            flash('Passwords do not match', 'warning')
        else:
            save_admin_password(new_password)
            flash('Admin password changed successfully', 'success')
            return redirect(url_for('admin_dashboard'))
    return render_template('admin_change_password.html')
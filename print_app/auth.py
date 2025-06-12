from flask import Blueprint, render_template, redirect, url_for, flash, request
from werkzeug.security import generate_password_hash
from flask_login import login_user, logout_user, login_required
from .models import User
from . import db

bp = Blueprint('auth', __name__, url_prefix='/auth')

@bp.route('/register', methods=('GET', 'POST'))
def register():
    if request.method == 'POST':
        username = request.form['username']
        email = request.form['email']
        password = request.form['password']
        error = None

        if not username:
            error = 'Username wajib diisi.'
        elif not email:
            error = 'Email wajib diisi.'
        elif not password:
            error = 'Password wajib diisi.'
        elif User.query.filter_by(username=username).first() is not None:
            error = f"User {username} sudah terdaftar."
        elif User.query.filter_by(email=email).first() is not None:
            error = f"Email {email} sudah terdaftar."

        if error is None:
            new_user = User(username=username, email=email)
            new_user.set_password(password)
            db.session.add(new_user)
            db.session.commit()
            flash('Registrasi berhasil! Silakan login.', 'success')
            return redirect(url_for('auth.login'))
        
        flash(error, 'danger')

    return render_template('register.html')

@bp.route('/login', methods=('GET', 'POST'))
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        remember = True if request.form.get('remember') else False
        error = None
        
        user = User.query.filter_by(username=username).first()

        if user is None or not user.check_password(password):
            error = 'Username atau password salah.'
        
        if error is None:
            login_user(user, remember=remember)
            flash('Login berhasil!', 'success')
            if user.is_admin:
                return redirect(url_for('admin.dashboard'))
            return redirect(url_for('main.index'))

        flash(error, 'danger')
        
    return render_template('login.html')

@bp.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('main.index'))
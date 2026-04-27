from datetime import datetime, timedelta
from flask import Blueprint, render_template, redirect, url_for, flash, request
from werkzeug.security import generate_password_hash
from flask_login import login_user, logout_user, login_required
from models import User
from extensions import db

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

    return render_template('auth/register.html')

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
        
    return render_template('auth/login.html')

@bp.route('/forgot-password', methods=('GET', 'POST'))
def forgot_password():
    if request.method == 'POST':
        email = request.form.get('email', '').strip()
        user = User.query.filter_by(email=email).first()
        
        if user:
            token = user.generate_reset_token()
            db.session.commit()
            flash(f'Token reset berhasil dibuat. Gunakan token berikut untuk reset password: {token}', 'success')
            return redirect(url_for('auth.reset_password', token=token))
        else:
            flash('Email tidak ditemukan dalam sistem.', 'danger')

    return render_template('auth/forgot_password.html')

@bp.route('/reset-password/<token>', methods=('GET', 'POST'))
def reset_password(token):
    user = User.query.filter_by(reset_token=token).first()
    
    if not user:
        flash('Token reset tidak valid atau sudah kedaluwarsa.', 'danger')
        return redirect(url_for('auth.forgot_password'))
    
    # Check if token is expired (30 minutes)
    if user.reset_token_expiry:
        expiry_time = user.reset_token_expiry + timedelta(minutes=30)
        if datetime.utcnow() > expiry_time:
            user.reset_token = None
            user.reset_token_expiry = None
            db.session.commit()
            flash('Token reset sudah kedaluwarsa. Silakan minta token baru.', 'danger')
            return redirect(url_for('auth.forgot_password'))
    
    if request.method == 'POST':
        password = request.form.get('password', '')
        confirm_password = request.form.get('confirm_password', '')
        
        if not password:
            flash('Password baru wajib diisi.', 'danger')
        elif password != confirm_password:
            flash('Password dan konfirmasi password tidak cocok.', 'danger')
        elif len(password) < 6:
            flash('Password minimal 6 karakter.', 'danger')
        else:
            user.set_password(password)
            user.reset_token = None
            user.reset_token_expiry = None
            db.session.commit()
            flash('Password berhasil direset! Silakan login dengan password baru.', 'success')
            return redirect(url_for('auth.login'))
    
    return render_template('auth/reset_password.html', token=token)

@bp.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('auth.login'))

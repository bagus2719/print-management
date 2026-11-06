import time
import re
from collections import defaultdict
from flask import Blueprint, render_template, redirect, url_for, flash, request
from werkzeug.security import generate_password_hash
from flask_login import login_user, logout_user, login_required
from models import User
from extensions import db

bp = Blueprint('auth', __name__, url_prefix='/auth')

# =====================================================================
# Rate Limiter In-Memory Sederhana untuk Keamanan Autentikasi
# =====================================================================
_LOGIN_ATTEMPTS = defaultdict(list)
MAX_LOGIN_ATTEMPTS = 5
LOCKOUT_WINDOW_SECONDS = 300  # 5 menit

def get_client_ip():
    """Mengambil alamat IP klien dengan aman, termasuk jika di balik reverse proxy."""
    if request.headers.get('X-Forwarded-For'):
        return request.headers.get('X-Forwarded-For').split(',')[0].strip()
    return request.remote_addr or '127.0.0.1'

def is_login_rate_limited(identifier):
    """Cek apakah IP/identifier telah melampaui batas percobaan login."""
    now = time.time()
    # Bersihkan percobaan di luar window 5 menit
    _LOGIN_ATTEMPTS[identifier] = [t for t in _LOGIN_ATTEMPTS[identifier] if now - t < LOCKOUT_WINDOW_SECONDS]
    return len(_LOGIN_ATTEMPTS[identifier]) >= MAX_LOGIN_ATTEMPTS

def record_failed_login(identifier):
    """Catat percobaan login gagal."""
    _LOGIN_ATTEMPTS[identifier].append(time.time())

def clear_login_attempts(identifier):
    """Reset percobaan login setelah berhasil."""
    _LOGIN_ATTEMPTS.pop(identifier, None)


@bp.route('/register', methods=('GET', 'POST'))
def register():
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        email = request.form.get('email', '').strip().lower() or None
        password = request.form.get('password', '')
        error = None

        if not username:
            error = 'Username wajib diisi.'
        elif len(username) < 3:
            error = 'Username minimal 3 karakter.'
        elif not re.match(r'^[a-zA-Z0-9_]+$', username):
            error = 'Username hanya boleh mengandung huruf, angka, dan underscore (_).'
        elif not password:
            error = 'Password wajib diisi.'
        elif len(password) < 6:
            error = 'Password minimal harus 6 karakter.'
        elif email and not re.match(r'^[^@]+@[^@]+\.[^@]+$', email):
            error = 'Format email tidak valid.'
        elif User.query.filter_by(username=username).first() is not None:
            error = f"Username '{username}' sudah digunakan."
        elif email and User.query.filter_by(email=email).first() is not None:
            error = f"Email '{email}' sudah terdaftar."

        if error is None:
            new_user = User(username=username, email=email)
            new_user.set_password(password)
            db.session.add(new_user)
            db.session.commit()
            flash('Registrasi berhasil! Silakan login dengan akun Anda.', 'success')
            return redirect(url_for('auth.login'))
        
        flash(error, 'danger')

    return render_template('auth/register.html')

@bp.route('/login', methods=('GET', 'POST'))
def login():
    if request.method == 'POST':
        client_ip = get_client_ip()
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '')
        remember = bool(request.form.get('remember'))
        error = None

        # 1. Cek Rate Limiting (Proteksi Brute-Force)
        if is_login_rate_limited(client_ip):
            flash('Terlalu banyak percobaan login gagal. Mohon tunggu 5 menit sebelum mencoba kembali.', 'danger')
            return render_template('auth/login.html')

        user = User.query.filter_by(username=username).first()

        if user is None or not user.check_password(password):
            record_failed_login(client_ip)
            attempts_left = MAX_LOGIN_ATTEMPTS - len(_LOGIN_ATTEMPTS[client_ip])
            if attempts_left > 0:
                error = f'Username atau password salah. Sisa percobaan: {attempts_left}.'
            else:
                error = 'Terlalu banyak percobaan login gagal. Akun terkunci sementara selama 5 menit.'
        
        if error is None:
            clear_login_attempts(client_ip)
            login_user(user, remember=remember)
            flash('Login berhasil!', 'success')
            if user.is_admin:
                return redirect(url_for('admin.dashboard'))
            return redirect(url_for('main.index'))

        flash(error, 'danger')
        
    return render_template('auth/login.html')

@bp.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('auth.login'))

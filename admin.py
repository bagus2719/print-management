from datetime import datetime, timedelta
import os
import time
from flask import Blueprint, render_template, request, flash, redirect, url_for, current_app
from flask_login import login_required, current_user
from werkzeug.utils import secure_filename
from functools import wraps
from models import PrintJob, User, Payment, PaymentAccount, ChatMessage
from extensions import db

bp = Blueprint('admin', __name__, url_prefix='/admin')

def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated or not current_user.is_admin:
            flash('Anda tidak memiliki izin untuk mengakses halaman ini.', 'danger')
            return redirect(url_for('main.index'))
        return f(*args, **kwargs)
    return decorated_function

@bp.route('/dashboard')
@login_required
@admin_required
def dashboard():
    total_jobs = PrintJob.query.count()
    total_users = User.query.filter(User.is_admin == False).count()
    pending_jobs = PrintJob.query.filter_by(status='pending').count()
    pending_payments = Payment.query.filter_by(status='pending').count()
    total_revenue = db.session.query(db.func.sum(Payment.amount)).filter_by(status='confirmed').scalar() or 0

    recent_jobs = PrintJob.query.order_by(PrintJob.upload_time.desc()).limit(5).all()
    recent_payments = Payment.query.order_by(Payment.created_at.desc()).limit(5).all()

    return render_template('admin/dashboard.html',
                           total_jobs=total_jobs,
                           total_users=total_users,
                           pending_jobs=pending_jobs,
                           pending_payments=pending_payments,
                           total_revenue=total_revenue,
                           recent_jobs=recent_jobs,
                           recent_payments=recent_payments)

# --- MANAGE JOBS ---
@bp.route('/jobs')
@login_required
@admin_required
def manage_jobs():
    status_filter = request.args.get('status', '')
    user_filter = request.args.get('user_id', '')
    sort_by = request.args.get('sort_by', 'time_desc')
    query = PrintJob.query.join(User, PrintJob.user_id == User.id)
    if status_filter:
        query = query.filter(PrintJob.status == status_filter)
    if user_filter:
        query = query.filter(PrintJob.user_id == user_filter)
    if sort_by == 'time_asc':
        query = query.order_by(PrintJob.upload_time.asc())
    elif sort_by == 'user_asc':
        query = query.order_by(User.username.asc())
    elif sort_by == 'cost_desc':
        query = query.order_by(PrintJob.total_cost.desc())
    else: 
        query = query.order_by(PrintJob.upload_time.desc())

    all_jobs = query.all()
    all_users = User.query.filter(User.is_admin == False).order_by(User.username).all()
    total_cost_filtered = sum(job.total_cost for job in all_jobs)

    return render_template('admin/jobs.html', 
                           jobs=all_jobs, 
                           users=all_users,
                           total_cost_filtered=total_cost_filtered,
                           current_status=status_filter,
                           current_user_id=user_filter,
                           current_sort_by=sort_by)

@bp.route('/update_status/<int:job_id>/<new_status>', methods=['POST'])
@login_required
@admin_required
def update_status(job_id, new_status):
    job = PrintJob.query.get_or_404(job_id)
    if new_status in ['pending', 'printing', 'completed', 'failed']:
        job.status = new_status
        db.session.commit()
        flash(f'Status pekerjaan "{job.display_name}" berhasil diubah menjadi {new_status}.', 'success')
    else:
        flash('Status tidak valid.', 'error')
    return redirect(request.referrer or url_for('admin.manage_jobs'))

@bp.route('/delete_job/<int:job_id>', methods=['POST'])
@login_required
@admin_required
def delete_job(job_id):
    job = PrintJob.query.get_or_404(job_id)
    db.session.delete(job)
    db.session.commit()
    flash(f'Pekerjaan "{job.display_name}" berhasil dihapus.', 'info')
    return redirect(request.referrer or url_for('admin.manage_jobs'))

@bp.route('/bulk_delete', methods=['POST'])
@login_required
@admin_required
def bulk_delete():
    job_ids = request.form.getlist('selected_jobs')
    if not job_ids:
        flash('Tidak ada pekerjaan yang dipilih untuk dihapus.', 'warning')
        return redirect(url_for('admin.manage_jobs'))
    
    jobs_to_delete = PrintJob.query.filter(PrintJob.id.in_(job_ids)).all()
    for job in jobs_to_delete:
        db.session.delete(job)
    db.session.commit()
    
    flash(f'{len(job_ids)} pekerjaan berhasil dihapus.', 'success')
    return redirect(request.referrer or url_for('admin.manage_jobs'))

# --- MANAGE USERS ---
@bp.route('/users')
@login_required
@admin_required
def manage_users():
    users = User.query.order_by(User.created_at.desc()).all()
    return render_template('admin/users.html', users=users)

@bp.route('/users/toggle_admin/<int:user_id>', methods=['POST'])
@login_required
@admin_required
def toggle_admin(user_id):
    user = User.query.get_or_404(user_id)
    if user.id == current_user.id:
        flash('Anda tidak bisa mengubah status admin Anda sendiri.', 'danger')
    else:
        user.is_admin = not user.is_admin
        db.session.commit()
        status = "admin" if user.is_admin else "user biasa"
        flash(f'User "{user.username}" berhasil diubah menjadi {status}.', 'success')
    return redirect(url_for('admin.manage_users'))

@bp.route('/users/delete/<int:user_id>', methods=['POST'])
@login_required
@admin_required
def delete_user(user_id):
    user = User.query.get_or_404(user_id)
    if user.id == current_user.id:
        flash('Anda tidak bisa menghapus akun Anda sendiri.', 'danger')
    else:
        db.session.delete(user)
        db.session.commit()
        flash(f'User "{user.username}" berhasil dihapus.', 'success')
    return redirect(url_for('admin.manage_users'))

@bp.route('/users/reset_password/<int:user_id>', methods=['POST'])
@login_required
@admin_required
def admin_reset_password(user_id):
    user = User.query.get_or_404(user_id)
    new_password = request.form.get('new_password', '').strip()
    if not new_password or len(new_password) < 6:
        flash('Password baru minimal 6 karakter.', 'danger')
    else:
        user.set_password(new_password)
        db.session.commit()
        flash(f'Password user "{user.username}" berhasil direset.', 'success')
    return redirect(url_for('admin.manage_users'))

# --- MANAGE PAYMENTS ---
@bp.route('/payments')
@login_required
@admin_required
def manage_payments():
    status_filter = request.args.get('status', '')
    query = Payment.query.join(User, Payment.user_id == User.id)
    if status_filter:
        query = query.filter(Payment.status == status_filter)
    payments = query.order_by(Payment.created_at.desc()).all()
    return render_template('admin/payments.html', payments=payments, current_status=status_filter)

@bp.route('/payments/confirm/<int:payment_id>', methods=['POST'])
@login_required
@admin_required
def confirm_payment(payment_id):
    payment = Payment.query.get_or_404(payment_id)
    payment.status = 'confirmed'
    payment.confirmed_at = datetime.utcnow()
    payment.job.payment_status = 'paid'
    db.session.commit()
    flash(f'Pembayaran #{payment.id} berhasil dikonfirmasi.', 'success')
    return redirect(url_for('admin.manage_payments'))

@bp.route('/payments/reject/<int:payment_id>', methods=['POST'])
@login_required
@admin_required
def reject_payment(payment_id):
    payment = Payment.query.get_or_404(payment_id)
    payment.status = 'rejected'
    payment.job.payment_status = 'unpaid'
    payment.notes = request.form.get('notes', '')
    db.session.commit()
    flash(f'Pembayaran #{payment.id} ditolak.', 'warning')
    return redirect(url_for('admin.manage_payments'))

@bp.route('/jobs/set_payment/<int:job_id>/<new_status>', methods=['POST'])
@login_required
@admin_required
def set_payment_status(job_id, new_status):
    """Admin mengatur status pembayaran secara manual (misal: bukti via WA)."""
    job = PrintJob.query.get_or_404(job_id)
    
    if new_status == 'paid':
        job.payment_status = 'paid'
        # Jika belum ada payment record, buat secara manual
        existing = Payment.query.filter_by(job_id=job.id).first()
        if not existing:
            manual_payment = Payment(
                job_id=job.id,
                user_id=job.user_id,
                amount=job.total_cost,
                method='manual',
                status='confirmed',
                confirmed_at=datetime.utcnow()
            )
            db.session.add(manual_payment)
        else:
            existing.status = 'confirmed'
            existing.confirmed_at = datetime.utcnow()
        flash(f'Pembayaran "{job.display_name}" ditandai LUNAS.', 'success')
    elif new_status == 'unpaid':
        job.payment_status = 'unpaid'
        flash(f'Pembayaran "{job.display_name}" direset ke BELUM BAYAR.', 'info')
    
    db.session.commit()
    return redirect(request.referrer or url_for('admin.manage_jobs'))


# --- MANAGE PAYMENT ACCOUNTS ---
@bp.route('/payment-accounts')
@login_required
@admin_required
def manage_payment_accounts():
    accounts = PaymentAccount.query.all()
    return render_template('admin/payment_accounts.html', accounts=accounts)

@bp.route('/payment-accounts/add', methods=['POST'])
@login_required
@admin_required
def add_payment_account():
    method = request.form.get('method', '').strip()
    label = request.form.get('label', '').strip()
    account_number = request.form.get('account_number', '').strip()
    account_name = request.form.get('account_name', '').strip()
    
    qr_filename = None
    if method == 'qris':
        qr_file = request.files.get('qr_file')
        if qr_file and qr_file.filename != '':
            qr_dir = os.path.join(current_app.config['UPLOAD_FOLDER'], 'qris')
            os.makedirs(qr_dir, exist_ok=True)
            qr_filename = f"qris_{int(time.time())}_{secure_filename(qr_file.filename)}"
            qr_file.save(os.path.join(qr_dir, qr_filename))

    if not all([method, label, account_number, account_name]):
        flash('Semua field teks wajib diisi.', 'danger')
    else:
        acc = PaymentAccount(method=method, label=label, account_number=account_number, account_name=account_name, qr_filename=qr_filename)
        db.session.add(acc)
        db.session.commit()
        flash(f'Akun pembayaran "{label}" berhasil ditambahkan.', 'success')
    return redirect(url_for('admin.manage_payment_accounts'))

@bp.route('/payment-accounts/edit/<int:acc_id>', methods=['POST'])
@login_required
@admin_required
def edit_payment_account(acc_id):
    acc = PaymentAccount.query.get_or_404(acc_id)
    acc.method = request.form.get('method', acc.method).strip()
    acc.label = request.form.get('label', acc.label).strip()
    acc.account_number = request.form.get('account_number', acc.account_number).strip()
    acc.account_name = request.form.get('account_name', acc.account_name).strip()
    
    if acc.method == 'qris':
        qr_file = request.files.get('qr_file')
        if qr_file and qr_file.filename != '':
            qr_dir = os.path.join(current_app.config['UPLOAD_FOLDER'], 'qris')
            os.makedirs(qr_dir, exist_ok=True)
            qr_filename = f"qris_{int(time.time())}_{secure_filename(qr_file.filename)}"
            qr_file.save(os.path.join(qr_dir, qr_filename))
            acc.qr_filename = qr_filename
            
    db.session.commit()
    flash(f'Akun "{acc.label}" berhasil diupdate.', 'success')
    return redirect(url_for('admin.manage_payment_accounts'))

@bp.route('/payment-accounts/toggle/<int:acc_id>', methods=['POST'])
@login_required
@admin_required
def toggle_payment_account(acc_id):
    acc = PaymentAccount.query.get_or_404(acc_id)
    acc.is_active = not acc.is_active
    db.session.commit()
    status = "aktif" if acc.is_active else "nonaktif"
    flash(f'Akun "{acc.label}" berhasil di-{status}-kan.', 'success')
    return redirect(url_for('admin.manage_payment_accounts'))

@bp.route('/payment-accounts/delete/<int:acc_id>', methods=['POST'])
@login_required
@admin_required
def delete_payment_account(acc_id):
    acc = PaymentAccount.query.get_or_404(acc_id)
    db.session.delete(acc)
    db.session.commit()
    flash(f'Akun "{acc.label}" berhasil dihapus.', 'success')
    return redirect(url_for('admin.manage_payment_accounts'))


# --- MANAGE CHATS ---
@bp.route('/chats')
@login_required
@admin_required
def manage_chats():
    # Cleanup old messages (> 7 days)
    week_ago = datetime.utcnow() - timedelta(days=7)
    deleted_count = ChatMessage.query.filter(ChatMessage.timestamp < week_ago).delete()
    if deleted_count > 0:
        db.session.commit()
        print(f"DEBUG: Deleted {deleted_count} old chat messages.")

    # Find all users who have sent messages
    subquery = db.session.query(
        ChatMessage.user_id,
        db.func.max(ChatMessage.timestamp).label('max_ts')
    ).group_by(ChatMessage.user_id).subquery()
    
    users_with_chats = User.query.join(subquery, User.id == subquery.c.user_id).order_by(subquery.c.max_ts.desc()).all()
    unread_counts = {u.id: ChatMessage.query.filter_by(user_id=u.id, is_from_admin=False, is_read=False).count() for u in users_with_chats}
    
    return render_template('admin/chats.html', users=users_with_chats, unread_counts=unread_counts)

@bp.route('/chats/view/<int:user_id>')
@login_required
@admin_required
def view_chat(user_id):
    target_user = User.query.get_or_404(user_id)
    messages = ChatMessage.query.filter_by(user_id=user_id).order_by(ChatMessage.timestamp.asc()).all()
    
    # Mark messages as read
    unread = ChatMessage.query.filter_by(user_id=user_id, is_from_admin=False, is_read=False).all()
    for m in unread:
        m.is_read = True
    db.session.commit()
    
    return render_template('admin/chat_view.html', target_user=target_user, messages=messages)

@bp.route('/chats/reply/<int:user_id>', methods=['POST'])
@login_required
@admin_required
def chat_reply(user_id):
    msg_text = request.form.get('message', '').strip()
    if msg_text:
        new_msg = ChatMessage(user_id=user_id, message=msg_text, is_from_admin=True)
        db.session.add(new_msg)
        db.session.commit()
    return redirect(url_for('admin.view_chat', user_id=user_id))

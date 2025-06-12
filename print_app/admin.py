from flask import Blueprint, render_template, request, flash, redirect, url_for
from flask_login import login_required, current_user
from functools import wraps
from .models import PrintJob, User
from . import db

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

    return render_template('admin.html', 
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
    return redirect(request.referrer or url_for('admin.dashboard'))

@bp.route('/delete_job/<int:job_id>', methods=['POST'])
@login_required
@admin_required
def delete_job(job_id):
    job = PrintJob.query.get_or_404(job_id)
    db.session.delete(job)
    db.session.commit()
    flash(f'Pekerjaan "{job.display_name}" berhasil dihapus.', 'info')
    return redirect(request.referrer or url_for('admin.dashboard'))

@bp.route('/bulk_delete', methods=['POST'])
@login_required
@admin_required
def bulk_delete():
    job_ids = request.form.getlist('selected_jobs')
    
    if not job_ids:
        flash('Tidak ada pekerjaan yang dipilih untuk dihapus.', 'warning')
        return redirect(url_for('admin.dashboard'))
    
    jobs_to_delete = PrintJob.query.filter(PrintJob.id.in_(job_ids)).all()
    for job in jobs_to_delete:
        db.session.delete(job)
            
    db.session.commit()
    
    flash(f'{len(job_ids)} pekerjaan berhasil dihapus.', 'success')
    return redirect(request.referrer or url_for('admin.dashboard'))
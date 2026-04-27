import os
import PyPDF2
import time
from flask import (
    Blueprint, render_template, request, redirect, url_for, flash, current_app, 
    send_from_directory, abort, session
)
from flask_login import login_required, current_user
from werkzeug.utils import secure_filename
from models import PrintJob, Payment, PaymentAccount
from extensions import db

bp = Blueprint('main', __name__)

ALLOWED_IMAGE_EXTENSIONS = {'png', 'jpg', 'jpeg', 'webp'}

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in current_app.config['ALLOWED_EXTENSIONS']

def allowed_image(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_IMAGE_EXTENSIONS

def calculate_cost(pages, copies, paper_source):
    if paper_source == 'bawa_sendiri':
        price_per_page = 150
    else:
        price_per_page = 300
    return price_per_page * pages * copies

@bp.route('/', methods=('GET', 'POST'))
@login_required
def index():
    if request.method == 'POST':
        uploaded_files = request.files.getlist('files')
        
        if not uploaded_files or uploaded_files[0].filename == '':
            flash('Tidak ada file yang dipilih.', 'warning')
            return redirect(request.url)

        files_for_configuration = []
        for file in uploaded_files:
            if file and allowed_file(file.filename):
                original_filename = secure_filename(file.filename)
                
                timestamp = int(time.time())
                unique_filename = f"{timestamp}_{original_filename}"
                filepath = os.path.join(current_app.config['UPLOAD_FOLDER'], unique_filename)
                
                file.save(filepath)
                try:
                    with open(filepath, 'rb') as f:
                        reader = PyPDF2.PdfReader(f)
                        num_pages = len(reader.pages)
                    
                    files_for_configuration.append({
                        'filename': unique_filename,
                        'display_name': original_filename,
                        'filepath': filepath,
                        'pages': num_pages
                    })
                except Exception as e:
                    flash(f'Gagal memproses file "{original_filename}": {e}', 'danger')
                    if os.path.exists(filepath):
                        os.remove(filepath)
            else:
                flash(f'File "{file.filename}" memiliki format yang tidak didukung. Harap upload PDF.', 'warning')

        if files_for_configuration:
            session['files_to_configure'] = files_for_configuration
            return redirect(url_for('main.configure_jobs'))
        else:
            flash('Tidak ada file PDF valid yang berhasil diupload.', 'danger')
            return redirect(request.url)

    recent_jobs = PrintJob.query.filter_by(user_id=current_user.id).order_by(PrintJob.upload_time.desc()).limit(5).all()
    return render_template('user/dashboard.html', recent_jobs=recent_jobs)

@bp.route('/configure', methods=['GET', 'POST'])
@login_required
def configure_jobs():
    files = session.get('files_to_configure')
    if not files:
        flash('Tidak ada file untuk dikonfigurasi. Silakan upload terlebih dahulu.', 'warning')
        return redirect(url_for('main.index'))

    if request.method == 'POST':
        paper_source = request.form.get('paper_source')
        
        for i, file_details in enumerate(files):
            copies = int(request.form.get(f'copies_{i}', 1))
            if copies > 0:
                cost = calculate_cost(pages=file_details['pages'], copies=copies, paper_source=paper_source)
                new_job = PrintJob(
                    filename=file_details['filename'],
                    display_name=file_details['display_name'],
                    filepath=file_details['filepath'],
                    pages=file_details['pages'],
                    copies=copies,
                    paper_source=paper_source,
                    total_cost=cost,
                    author=current_user
                )
                db.session.add(new_job)

        db.session.commit()
        session.pop('files_to_configure', None)
        flash(f'{len(files)} pekerjaan berhasil ditambahkan ke antrian!', 'success')
        return redirect(url_for('main.history'))

    return render_template('user/configure.html', files=files)

@bp.route('/history')
@login_required
def history():
    sort_by = request.args.get('sort_by', 'time_desc')
    query = PrintJob.query.filter_by(user_id=current_user.id)
    if sort_by == 'time_asc':
        query = query.order_by(PrintJob.upload_time.asc())
    elif sort_by == 'cost_desc':
        query = query.order_by(PrintJob.total_cost.desc())
    elif sort_by == 'cost_asc':
        query = query.order_by(PrintJob.total_cost.asc())
    else:
        query = query.order_by(PrintJob.upload_time.desc())

    user_jobs = query.all()
    total_cost_all = sum(job.total_cost for job in user_jobs)
    
    # Quick Stats Data
    recent_jobs = PrintJob.query.filter_by(user_id=current_user.id).order_by(PrintJob.upload_time.desc()).limit(5).all()
    total_cost_recent = sum(job.total_cost for job in recent_jobs)

    return render_template('user/history.html', 
                           jobs=user_jobs,
                           total_cost_all=total_cost_all,
                           recent_jobs=recent_jobs,
                           total_cost_recent=total_cost_recent,
                           current_sort_by=sort_by)

@bp.route('/profile', methods=['GET', 'POST'])
@login_required
def profile():
    if request.method == 'POST':
        username = request.form.get('username')
        email = request.form.get('email')
        password = request.form.get('password')

        if username and username != current_user.username:
            current_user.username = username
        if email and email != current_user.email:
            current_user.email = email
        if password:
            current_user.set_password(password)

        db.session.commit()
        flash('Profil berhasil diperbarui!', 'success')
        return redirect(url_for('main.profile'))

    return render_template('user/profile.html')

@bp.route('/payment/<int:job_id>', methods=['GET', 'POST'])
@login_required
def payment(job_id):
    job = PrintJob.query.get_or_404(job_id)
    if job.user_id != current_user.id:
        abort(403)
    
    if job.payment_status == 'paid':
        flash('Pekerjaan ini sudah dibayar.', 'warning')
        return redirect(url_for('main.history'))
    
    existing_payment = Payment.query.filter_by(job_id=job.id, status='pending').first()
    if existing_payment:
        flash('Pembayaran untuk pekerjaan ini sedang menunggu konfirmasi admin.', 'warning')
        return redirect(url_for('main.history'))

    accounts = PaymentAccount.query.filter_by(is_active=True).all()

    if request.method == 'POST':
        method = request.form.get('payment_method')
        account_name = request.form.get('account_name', '').strip()
        proof_file = request.files.get('proof_file')
        
        if not method:
            flash('Pilih metode pembayaran.', 'danger')
        elif not account_name:
            flash('Nama pengirim wajib diisi.', 'danger')
        elif not proof_file or proof_file.filename == '':
            flash('Upload bukti transfer wajib diisi.', 'danger')
        elif not allowed_image(proof_file.filename):
            flash('Format bukti transfer harus PNG, JPG, JPEG, atau WEBP.', 'danger')
        else:
            # Save proof file
            proof_dir = os.path.join(current_app.config['UPLOAD_FOLDER'], 'proofs')
            os.makedirs(proof_dir, exist_ok=True)
            proof_name = f"proof_{int(time.time())}_{secure_filename(proof_file.filename)}"
            proof_file.save(os.path.join(proof_dir, proof_name))

            new_payment = Payment(
                job_id=job.id,
                user_id=current_user.id,
                amount=job.total_cost,
                method=method,
                account_name=account_name,
                proof_filename=proof_name
            )
            job.payment_status = 'waiting'
            db.session.add(new_payment)
            db.session.commit()
            flash('Pembayaran berhasil dikirim! Menunggu konfirmasi admin.', 'success')
            return redirect(url_for('main.history'))
    
    return render_template('user/payment.html', job=job, accounts=accounts)

@bp.route('/view_pdf/<int:job_id>')
@login_required
def view_pdf(job_id):
    job = PrintJob.query.get_or_404(job_id)
    if not current_user.is_admin and job.user_id != current_user.id:
        abort(403)
    try:
        return send_from_directory(
            directory=current_app.config['UPLOAD_FOLDER'],
            path=job.filename,
            mimetype='application/pdf'
        )
    except FileNotFoundError:
        abort(404)

@bp.route('/download_pdf/<int:job_id>')
@login_required
def download_pdf(job_id):
    job = PrintJob.query.get_or_404(job_id)
    if not current_user.is_admin:
        abort(403)
    try:
        return send_from_directory(
            directory=current_app.config['UPLOAD_FOLDER'],
            path=job.filename,
            as_attachment=True
        )
    except FileNotFoundError:
        abort(404)

@bp.route('/proof/<filename>')
@login_required
def view_proof(filename):
    proof_dir = os.path.join(current_app.config['UPLOAD_FOLDER'], 'proofs')
    try:
        return send_from_directory(directory=proof_dir, path=filename)
    except FileNotFoundError:
        abort(404)

@bp.route('/qris_image/<filename>')
def view_qris_image(filename):
    qr_dir = os.path.join(current_app.config['UPLOAD_FOLDER'], 'qris')
    try:
        return send_from_directory(directory=qr_dir, path=filename)
    except FileNotFoundError:
        abort(404)

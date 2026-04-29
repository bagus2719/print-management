import os
import PyPDF2
import time
from flask import (
    Blueprint, render_template, request, redirect, url_for, flash, current_app, 
    send_from_directory, abort, session, jsonify
)
from flask_login import login_required, current_user
from werkzeug.utils import secure_filename
from models import PrintJob, Payment, PaymentAccount, PrintPricing, ChatMessage
from extensions import db
import midtransclient
from PIL import Image

bp = Blueprint('main', __name__)

ALLOWED_IMAGE_EXTENSIONS = {'png', 'jpg', 'jpeg', 'webp'}

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in current_app.config['ALLOWED_EXTENSIONS']

def allowed_image(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_IMAGE_EXTENSIONS

def calculate_cost(pages, copies, color_mode, paper_size, paper_source):
    # Dynamic pricing based on PrintPricing DB
    # We will fetch prices from DB, if not exist, use defaults
    def get_price(key, default):
        p = PrintPricing.query.filter_by(setting_key=key).first()
        return p.price if p else default

    base_bw = get_price('A4_BW', 250)
    base_color = get_price('A4_COLOR', 300)
    discount_self = get_price('DISCOUNT_SELF', 150)
    
    mult_a4 = get_price('MULT_A4', 1.0)
    mult_f4 = get_price('MULT_F4', 1.0)
    mult_a3 = get_price('MULT_A3', 2.0)

    # Base price
    price_per_page = base_bw if color_mode == 'bw' else base_color
    
    # Multiplier
    multiplier = mult_a4
    if paper_size == 'F4':
        multiplier = mult_f4
    elif paper_size == 'A3':
        multiplier = mult_a3
        
    price_per_page = price_per_page * multiplier
    
    # Discount
    if paper_source == 'bawa_sendiri':
        price_per_page -= discount_self
        
    if price_per_page < 0:
        price_per_page = 0
        
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
                    num_pages = 1
                    if allowed_image(unique_filename):
                        # Use PIL to verify it's a valid image
                        with Image.open(filepath) as img:
                            img.verify()
                        num_pages = 1
                    else:
                        # It's a PDF
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
                    flash(f'Gagal memproses file "{original_filename}": format file mungkin rusak.', 'danger')
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
        paper_source = request.form.get('paper_source', 'dari_kami')
        
        for i, file_details in enumerate(files):
            copies = int(request.form.get(f'copies_{i}', 1))
            color_mode = request.form.get(f'color_{i}', 'bw')
            paper_size = request.form.get(f'size_{i}', 'A4')
            is_duplex = request.form.get(f'duplex_{i}', '0') == '1'

            if copies > 0:
                cost = calculate_cost(pages=file_details['pages'], copies=copies, color_mode=color_mode, paper_size=paper_size, paper_source=paper_source)
                new_job = PrintJob(
                    filename=file_details['filename'],
                    display_name=file_details['display_name'],
                    filepath=file_details['filepath'],
                    pages=file_details['pages'],
                    copies=copies,
                    color_mode=color_mode,
                    paper_size=paper_size,
                    paper_source=paper_source,
                    is_duplex=is_duplex,
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
        password = request.form.get('password')

        if username and username != current_user.username:
            current_user.username = username
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

    if request.method == 'POST':
        existing_payment = Payment.query.filter_by(job_id=job.id, method='midtrans', status='pending').first()
        
        snap = midtransclient.Snap(
            is_production=current_app.config.get('MIDTRANS_IS_PRODUCTION', False),
            server_key=current_app.config.get('MIDTRANS_SERVER_KEY'),
            client_key=current_app.config.get('MIDTRANS_CLIENT_KEY')
        )
        order_id = f"ORDER-{job.id}-{int(time.time())}"
        param = {
            "transaction_details": {
                "order_id": order_id,
                "gross_amount": int(job.total_cost)
            },
            "customer_details": {
                "first_name": current_user.username,
                "email": "customer@printmanager.com"
            }
        }
        try:
            transaction = snap.create_transaction(param)
            snap_token = transaction['token']
            
            if not existing_payment:
                new_payment = Payment(
                    job_id=job.id,
                    user_id=current_user.id,
                    amount=job.total_cost,
                    method='midtrans',
                    midtrans_transaction_id=order_id,
                    status='pending'
                )
                db.session.add(new_payment)
                db.session.commit()
            else:
                existing_payment.midtrans_transaction_id = order_id
                db.session.commit()
                
            return jsonify({'token': snap_token})
        except Exception as e:
            return jsonify({'error': str(e)}), 500

    accounts = PaymentAccount.query.filter_by(is_active=True).all()
    return render_template('user/payment.html', job=job, accounts=accounts)


@bp.route('/payment_cash/<int:job_id>', methods=['POST'])
@login_required
def payment_cash(job_id):
    """Pembayaran tunai (cash) — status menunggu konfirmasi admin."""
    job = PrintJob.query.get_or_404(job_id)
    if job.user_id != current_user.id:
        abort(403)
    if job.payment_status == 'paid':
        flash('Pekerjaan ini sudah dibayar.', 'warning')
        return redirect(url_for('main.history'))
    
    existing = Payment.query.filter_by(job_id=job.id, method='cash', status='pending').first()
    if existing:
        flash('Pembayaran cash sudah tercatat. Silakan bayar langsung ke admin.', 'info')
        return redirect(url_for('main.history'))
    
    new_payment = Payment(
        job_id=job.id,
        user_id=current_user.id,
        amount=job.total_cost,
        method='cash',
        status='pending'
    )
    job.payment_status = 'waiting'
    db.session.add(new_payment)
    db.session.commit()
    
    flash('Pembayaran cash tercatat! Silakan bayar langsung ke admin.', 'success')
    return redirect(url_for('main.history'))

@bp.route('/payment/transfer/<int:job_id>', methods=['POST'])
@login_required
def payment_transfer(job_id):
    job = PrintJob.query.get_or_404(job_id)
    if job.user_id != current_user.id:
        abort(403)
    
    method = request.form.get('method')
    proof_file = request.files.get('proof_file')
    
    if not method:
        flash('Silakan pilih metode pembayaran.', 'danger')
        return redirect(url_for('main.payment', job_id=job.id))
    
    # Save proof file jika ada
    filename = None
    if proof_file and proof_file.filename:
        filename = f"proof_{job.id}_{int(time.time())}_{secure_filename(proof_file.filename)}"
        proof_path = os.path.join(current_app.config['UPLOAD_FOLDER'], 'proofs')
        os.makedirs(proof_path, exist_ok=True)
        proof_file.save(os.path.join(proof_path, filename))
    
    new_payment = Payment(
        job_id=job.id,
        user_id=current_user.id,
        amount=job.total_cost,
        method=method,
        proof_filename=filename,
        status='pending'
    )
    job.payment_status = 'waiting'
    db.session.add(new_payment)
    db.session.commit()
    
    flash('Pembayaran tercatat! Menunggu konfirmasi admin.', 'success')
    return redirect(url_for('main.history'))

from extensions import csrf
from datetime import datetime

@bp.route('/midtrans_webhook', methods=['POST'])
@csrf.exempt
def midtrans_webhook():
    data = request.json
    if not data:
        return jsonify({'status': 'error'}), 400
        
    order_id = data.get('order_id')
    transaction_status = data.get('transaction_status')
    
    if order_id and transaction_status in ['capture', 'settlement']:
        payment = Payment.query.filter_by(midtrans_transaction_id=order_id).first()
        if payment:
            payment.status = 'confirmed'
            payment.confirmed_at = datetime.utcnow()
            payment.job.payment_status = 'paid'
            db.session.commit()
            
    return jsonify({'status': 'ok'})


@bp.route('/check_payment_status/<int:job_id>', methods=['POST'])
@login_required
def check_payment_status(job_id):
    """Cek status transaksi langsung ke Midtrans API (fallback jika webhook tidak tersedia)."""
    job = PrintJob.query.get_or_404(job_id)
    if job.user_id != current_user.id:
        abort(403)
    
    payment = Payment.query.filter_by(job_id=job.id, method='midtrans').first()
    if not payment or not payment.midtrans_transaction_id:
        return jsonify({'status': 'not_found'}), 404
    
    # Jika sudah confirmed, tidak perlu cek lagi
    if payment.status == 'confirmed':
        return jsonify({'status': 'paid'})
    
    try:
        core = midtransclient.CoreApi(
            is_production=current_app.config.get('MIDTRANS_IS_PRODUCTION', False),
            server_key=current_app.config.get('MIDTRANS_SERVER_KEY'),
            client_key=current_app.config.get('MIDTRANS_CLIENT_KEY')
        )
        
        status_response = core.transactions.status(payment.midtrans_transaction_id)
        transaction_status = status_response.get('transaction_status', '')
        
        if transaction_status in ['capture', 'settlement']:
            payment.status = 'confirmed'
            payment.confirmed_at = datetime.utcnow()
            job.payment_status = 'paid'
            db.session.commit()
            return jsonify({'status': 'paid'})
        elif transaction_status == 'pending':
            return jsonify({'status': 'pending'})
        elif transaction_status in ['deny', 'cancel', 'expire']:
            payment.status = 'failed'
            db.session.commit()
            return jsonify({'status': 'failed'})
        else:
            return jsonify({'status': transaction_status})
            
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500

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


# === Halaman Kebijakan (Midtrans KYC) ===

@bp.route('/terms')
def terms():
    return render_template('pages/terms.html')

@bp.route('/privacy')
def privacy():
    return render_template('pages/privacy.html')

@bp.route('/refund')
def refund():
    return render_template('pages/refund.html')


# === Fitur Live Chat (User Side) ===

@bp.route('/chat/send', methods=['POST'])
@login_required
def chat_send():
    message_text = request.form.get('message')
    if not message_text:
        return jsonify({'error': 'Pesan kosong'}), 400
    
    new_msg = ChatMessage(
        user_id=current_user.id,
        message=message_text,
        is_from_admin=False
    )
    db.session.add(new_msg)
    db.session.commit()
    return jsonify({'status': 'ok'})

@bp.route('/chat/messages')
@login_required
def chat_messages():
    messages = ChatMessage.query.filter_by(user_id=current_user.id).order_by(ChatMessage.timestamp.asc()).all()
    # Mark as read when user opens
    unread_admin_msgs = ChatMessage.query.filter_by(user_id=current_user.id, is_from_admin=True, is_read=False).all()
    for m in unread_admin_msgs:
        m.is_read = True
    db.session.commit()

    return jsonify([{
        'message': m.message,
        'is_from_admin': m.is_from_admin,
        'time': m.timestamp.strftime('%H:%M')
    } for m in messages])

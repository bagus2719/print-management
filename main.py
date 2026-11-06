import os
import re
import json
import secrets
import PyPDF2
import time
import zipfile
import xml.etree.ElementTree as ET

# Fix for PythonAnywhere free tier outbound proxy
if 'PYTHONANYWHERE_SITE' in os.environ:
    os.environ['http_proxy'] = 'http://proxy.server:3128'
    os.environ['https_proxy'] = 'http://proxy.server:3128'

from flask import (
    Blueprint, render_template, request, redirect, url_for, flash, current_app, 
    send_from_directory, abort, session, jsonify
)
from flask_login import login_required, current_user
from werkzeug.utils import secure_filename
from models import PrintJob, Payment, PaymentAccount, PrintPricing, ChatMessage, utc_now
from extensions import db
import midtransclient
from PIL import Image

bp = Blueprint('main', __name__)

ALLOWED_IMAGE_EXTENSIONS = {'png', 'jpg', 'jpeg', 'webp'}
DOCUMENT_EXTENSIONS = {'doc', 'docx', 'ppt', 'pptx', 'xls', 'xlsx'}

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in current_app.config['ALLOWED_EXTENSIONS']

def allowed_image(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_IMAGE_EXTENSIONS

def get_office_page_count(filepath, ext):
    """Auto-detect page/slide count from Office Open XML files (.docx, .pptx, .xlsx).
    Uses built-in zipfile + xml modules, no extra libraries needed.
    Returns 1 as fallback if detection fails.
    """
    try:
        if ext == 'docx':
            # DOCX stores page count in docProps/app.xml
            with zipfile.ZipFile(filepath, 'r') as z:
                if 'docProps/app.xml' in z.namelist():
                    with z.open('docProps/app.xml') as f:
                        tree = ET.parse(f)
                        root = tree.getroot()
                        ns = '{http://schemas.openxmlformats.org/officeDocument/2006/extended-properties}'
                        pages_el = root.find(f'{ns}Pages')
                        if pages_el is not None and pages_el.text:
                            return max(1, int(pages_el.text))
        
        elif ext == 'pptx':
            # PPTX: count slide files inside ppt/slides/
            with zipfile.ZipFile(filepath, 'r') as z:
                slides = [n for n in z.namelist() if n.startswith('ppt/slides/slide') and n.endswith('.xml')]
                if slides:
                    return len(slides)
        
        elif ext == 'xlsx':
            # XLSX: count worksheet files inside xl/worksheets/
            with zipfile.ZipFile(filepath, 'r') as z:
                sheets = [n for n in z.namelist() if n.startswith('xl/worksheets/sheet') and n.endswith('.xml')]
                if sheets:
                    return len(sheets)
    except Exception:
        pass
    
    # Fallback for old binary formats (.doc, .ppt, .xls) or if detection fails
    return 1

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

def _save_upload_session(files_data):
    """Menyimpan data file upload ke file JSON server agar session cookie tidak overflow."""
    session_dir = os.path.join(current_app.instance_path, 'upload_sessions')
    os.makedirs(session_dir, exist_ok=True)
    token = secrets.token_hex(16)
    file_path = os.path.join(session_dir, f"{token}.json")
    with open(file_path, 'w', encoding='utf-8') as f:
        json.dump(files_data, f)
    return token

def _load_upload_session(token):
    """Membaca data file upload dari file JSON server."""
    if not token:
        return None
    file_path = os.path.join(current_app.instance_path, 'upload_sessions', f"{token}.json")
    if not os.path.exists(file_path):
        return None
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception:
        return None

def _clear_upload_session(token):
    """Menghapus file upload session dari server setelah selesai dikonfigurasi."""
    if not token:
        return
    file_path = os.path.join(current_app.instance_path, 'upload_sessions', f"{token}.json")
    try:
        if os.path.exists(file_path):
            os.remove(file_path)
    except OSError:
        pass

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
                    ext = unique_filename.rsplit('.', 1)[1].lower()
                    if ext in ALLOWED_IMAGE_EXTENSIONS:
                        # Use PIL to verify it's a valid image
                        with Image.open(filepath) as img:
                            img.verify()
                        num_pages = 1
                    elif ext == 'pdf':
                        # It's a PDF
                        with open(filepath, 'rb') as f:
                            reader = PyPDF2.PdfReader(f)
                            num_pages = len(reader.pages)
                    elif ext in DOCUMENT_EXTENSIONS:
                        # Auto-detect page/slide count from Office files
                        num_pages = get_office_page_count(filepath, ext)
                    else:
                        num_pages = 1
                    
                    files_for_configuration.append({
                        'filename': unique_filename,
                        'display_name': original_filename,
                        'filepath': filepath,
                        'pages': num_pages,
                        'ext': ext
                    })
                except Exception as e:
                    flash(f'Gagal memproses file "{original_filename}": format file mungkin rusak.', 'danger')
                    if os.path.exists(filepath):
                        os.remove(filepath)
            else:
                flash(f'File "{file.filename}" memiliki format yang tidak didukung. Harap upload PDF, Word, atau Gambar.', 'warning')

        if files_for_configuration:
            session_token = _save_upload_session(files_for_configuration)
            session['upload_config_token'] = session_token
            return redirect(url_for('main.configure_jobs'))
        else:
            flash('Tidak ada file valid yang berhasil diupload.', 'danger')
            return redirect(request.url)

    recent_jobs = PrintJob.query.filter_by(user_id=current_user.id).order_by(PrintJob.upload_time.desc()).limit(5).all()
    return render_template('user/dashboard.html', recent_jobs=recent_jobs)

@bp.route('/configure', methods=['GET', 'POST'])
@login_required
def configure_jobs():
    session_token = session.get('upload_config_token')
    files = _load_upload_session(session_token)
    if not files:
        flash('Tidak ada file untuk dikonfigurasi atau sesi telah berakhir. Silakan upload terlebih dahulu.', 'warning')
        return redirect(url_for('main.index'))

    if request.method == 'POST':
        paper_source = request.form.get('paper_source', 'dari_kami')
        
        for i, file_details in enumerate(files):
            pages = int(request.form.get(f'pages_{i}', file_details['pages']))
            copies = int(request.form.get(f'copies_{i}', 1))
            color_mode = request.form.get(f'color_{i}', 'bw')
            paper_size = request.form.get(f'size_{i}', 'A4')
            is_duplex = request.form.get(f'duplex_{i}', '0') == '1'

            if copies > 0:
                cost = calculate_cost(pages=pages, copies=copies, color_mode=color_mode, paper_size=paper_size, paper_source=paper_source)
                new_job = PrintJob(
                    filename=file_details['filename'],
                    display_name=file_details['display_name'],
                    filepath=file_details['filepath'],
                    pages=pages,
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
        _clear_upload_session(session_token)
        session.pop('upload_config_token', None)
        flash(f'{len(files)} pekerjaan berhasil ditambahkan ke antrian!', 'success')
        return redirect(url_for('main.history'))

    def get_price(key, default):
        p = PrintPricing.query.filter_by(setting_key=key).first()
        return p.price if p else default
        
    pricing = {
        'A4_BW': get_price('A4_BW', 250),
        'A4_COLOR': get_price('A4_COLOR', 300),
        'DISCOUNT_SELF': get_price('DISCOUNT_SELF', 150),
        'MULT_A4': get_price('MULT_A4', 1.0),
        'MULT_F4': get_price('MULT_F4', 1.0),
        'MULT_A3': get_price('MULT_A3', 2.0),
    }

    return render_template('user/configure.html', files=files, pricing=pricing)

@bp.route('/history')
@login_required
def history():
    sort_by = request.args.get('sort_by', 'time_desc')
    page = request.args.get('page', 1, type=int)
    per_page = 10

    query = PrintJob.query.filter_by(user_id=current_user.id)
    if sort_by == 'time_asc':
        query = query.order_by(PrintJob.upload_time.asc())
    elif sort_by == 'cost_desc':
        query = query.order_by(PrintJob.total_cost.desc())
    elif sort_by == 'cost_asc':
        query = query.order_by(PrintJob.total_cost.asc())
    else:
        query = query.order_by(PrintJob.upload_time.desc())

    # Pagination
    pagination = query.paginate(page=page, per_page=per_page, error_out=False)
    user_jobs = pagination.items

    # Statistik Akurat (seluruh riwayat user)
    total_cost_all = db.session.query(db.func.sum(PrintJob.total_cost)).filter_by(user_id=current_user.id).scalar() or 0.0
    completed_jobs_count = PrintJob.query.filter_by(user_id=current_user.id, status='completed').count()
    pending_jobs_count = PrintJob.query.filter_by(user_id=current_user.id, status='pending').count()
    
    # Quick Stats Data
    recent_jobs = PrintJob.query.filter_by(user_id=current_user.id).order_by(PrintJob.upload_time.desc()).limit(5).all()
    total_cost_recent = sum(job.total_cost for job in recent_jobs)

    return render_template('user/history.html', 
                           jobs=user_jobs,
                           pagination=pagination,
                           total_cost_all=total_cost_all,
                           completed_jobs_count=completed_jobs_count,
                           pending_jobs_count=pending_jobs_count,
                           recent_jobs=recent_jobs,
                           total_cost_recent=total_cost_recent,
                           current_sort_by=sort_by)

@bp.route('/profile', methods=['GET', 'POST'])
@login_required
def profile():
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        email = request.form.get('email', '').strip().lower() or None
        password = request.form.get('password', '')

        if username and username != current_user.username:
            if len(username) < 3 or not re.match(r'^[a-zA-Z0-9_]+$', username):
                flash('Username minimal 3 karakter dan hanya huruf/angka/underscore.', 'danger')
                return redirect(url_for('main.profile'))
            existing_user = User.query.filter_by(username=username).first()
            if existing_user and existing_user.id != current_user.id:
                flash(f"Username '{username}' sudah digunakan.", 'danger')
                return redirect(url_for('main.profile'))
            current_user.username = username

        if email != current_user.email:
            if email and not re.match(r'^[^@]+@[^@]+\.[^@]+$', email):
                flash('Format email tidak valid.', 'danger')
                return redirect(url_for('main.profile'))
            if email:
                existing_email = User.query.filter_by(email=email).first()
                if existing_email and existing_email.id != current_user.id:
                    flash(f"Email '{email}' sudah terdaftar untuk akun lain.", 'danger')
                    return redirect(url_for('main.profile'))
            current_user.email = email

        if password:
            if len(password) < 6:
                flash('Password baru minimal 6 karakter.', 'danger')
                return redirect(url_for('main.profile'))
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

import hashlib
from extensions import csrf
from datetime import datetime

def verify_midtrans_signature(data, server_key):
    """Verifikasi signature key dari notifikasi webhook Midtrans."""
    order_id = str(data.get('order_id', ''))
    status_code = str(data.get('status_code', ''))
    gross_amount = str(data.get('gross_amount', ''))
    received_signature = data.get('signature_key', '')

    if not all([order_id, status_code, gross_amount, received_signature, server_key]):
        return False

    raw_signature_str = f"{order_id}{status_code}{gross_amount}{server_key}"
    calculated_signature = hashlib.sha512(raw_signature_str.encode('utf-8')).hexdigest()
    return calculated_signature.lower() == str(received_signature).lower()

@bp.route('/midtrans_webhook', methods=['POST'])
@csrf.exempt
def midtrans_webhook():
    data = request.get_json(silent=True)
    if not data:
        return jsonify({'status': 'error', 'message': 'Payload JSON tidak valid'}), 400

    server_key = current_app.config.get('MIDTRANS_SERVER_KEY')
    if not server_key:
        return jsonify({'status': 'error', 'message': 'MIDTRANS_SERVER_KEY belum dikonfigurasi'}), 500

    # 1. Verifikasi Keaslian Notifikasi (Signature Key)
    if not verify_midtrans_signature(data, server_key):
        return jsonify({'status': 'error', 'message': 'Signature tidak valid'}), 403

    order_id = data.get('order_id')
    transaction_status = data.get('transaction_status')
    fraud_status = data.get('fraud_status')

    payment = Payment.query.filter_by(midtrans_transaction_id=order_id).first()
    if not payment:
        return jsonify({'status': 'error', 'message': 'Data transaksi pembayaran tidak ditemukan'}), 404

    # 2. Update status berdasarkan status transaksi Midtrans
    if transaction_status == 'capture':
        if fraud_status == 'accept':
            payment.status = 'confirmed'
            payment.confirmed_at = utc_now()
            if payment.job:
                payment.job.payment_status = 'paid'
        elif fraud_status == 'challenge':
            payment.status = 'challenge'
    elif transaction_status == 'settlement':
        payment.status = 'confirmed'
        payment.confirmed_at = utc_now()
        if payment.job:
            payment.job.payment_status = 'paid'
    elif transaction_status in ['deny', 'cancel', 'expire']:
        payment.status = 'failed'
        if payment.job:
            payment.job.payment_status = 'unpaid'
    elif transaction_status == 'pending':
        payment.status = 'pending'

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
            payment.confirmed_at = utc_now()
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

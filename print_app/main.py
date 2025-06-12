import os
import PyPDF2
from flask import Blueprint, render_template, request, redirect, url_for, flash, current_app
from flask_login import login_required, current_user
from werkzeug.utils import secure_filename
from .models import PrintJob
from . import db

bp = Blueprint('main', __name__)

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in current_app.config['ALLOWED_EXTENSIONS']

def calculate_cost(pages, copies, print_type, paper_source):
    if paper_source == 'bawa_sendiri':
        base_price_per_page = 150
    else:
        base_price_per_page = 300
    
    if print_type == 'color':
        final_price_per_page = base_price_per_page
    else:
        final_price_per_page = base_price_per_page
        
    return final_price_per_page * pages * copies

@bp.route('/', methods=('GET', 'POST'))
@login_required
def index():
    if request.method == 'POST':
        if 'file' not in request.files:
            flash('Tidak ada file yang dipilih', 'warning')
            return redirect(request.url)
        file = request.files['file']
        if file.filename == '':
            flash('Tidak ada file yang dipilih', 'warning')
            return redirect(request.url)
        
        if file and allowed_file(file.filename):
            filename = secure_filename(file.filename)
            filepath = os.path.join(current_app.config['UPLOAD_FOLDER'], filename)
            file.save(filepath)
            try:
                with open(filepath, 'rb') as f:
                    reader = PyPDF2.PdfReader(f)
                    num_pages = len(reader.pages)
            except Exception as e:
                flash(f'Error membaca file PDF: {e}', 'danger')
                return redirect(request.url)

            copies = int(request.form.get('copies', 1))
            print_type = request.form.get('print_type', 'grayscale')
            paper_size = request.form.get('paper_size', 'A4')
            paper_source = request.form.get('paper_source', 'dari_kami')
            cost = calculate_cost(num_pages, copies, print_type, paper_source)
            new_job = PrintJob(
                filename=filename,
                filepath=filepath,
                pages=num_pages,
                copies=copies,
                print_type=print_type,
                paper_size=paper_size,
                paper_source=paper_source,
                total_cost=cost,
                author=current_user
            )
            db.session.add(new_job)
            db.session.commit()
            flash('File berhasil diupload! Silakan lakukan konfirmasi pembayaran.', 'success')
            return redirect(url_for('main.index'))
        else:
            flash('Jenis file tidak diizinkan. Harap upload PDF.', 'danger')

    user_jobs = PrintJob.query.filter_by(user_id=current_user.id).order_by(PrintJob.upload_time.desc()).limit(5).all()
    total_cost_recent = sum(job.total_cost for job in user_jobs)

    return render_template('index.html', 
                           user_jobs=user_jobs,
                           total_cost_recent=total_cost_recent)

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

    return render_template('history.html', 
                           jobs=user_jobs,
                           total_cost_all=total_cost_all,
                           current_sort_by=sort_by)
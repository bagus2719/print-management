import secrets
from datetime import datetime
from werkzeug.security import generate_password_hash, check_password_hash
from flask_login import UserMixin
from extensions import db, login_manager

class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(64), index=True, unique=True, nullable=False)
    password_hash = db.Column(db.String(256))
    is_admin = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    jobs = db.relationship('PrintJob', backref='author', lazy='dynamic')
    payments = db.relationship('Payment', backref='payer', lazy='dynamic')

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

@login_manager.user_loader
def load_user(id):
    return User.query.get(int(id))

class PrintPricing(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    setting_key = db.Column(db.String(50), unique=True, nullable=False) # e.g. 'A4_BW', 'A4_COLOR', 'BAWA_KERTAS_DISCOUNT'
    setting_name = db.Column(db.String(100), nullable=False)
    price = db.Column(db.Float, nullable=False)
    description = db.Column(db.String(255), nullable=True)

class PrintJob(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    filename = db.Column(db.String(255), nullable=False, unique=True)
    display_name = db.Column(db.String(255), nullable=False)
    filepath = db.Column(db.String(512), nullable=False)
    pages = db.Column(db.Integer, nullable=False)
    copies = db.Column(db.Integer, default=1)
    
    # Konfigurasi Detail
    color_mode = db.Column(db.String(50), default='bw') # 'bw' or 'color'
    paper_size = db.Column(db.String(50), default='A4')
    paper_source = db.Column(db.String(50), default='dari_kami', nullable=False)
    is_duplex = db.Column(db.Boolean, default=False)
    
    total_cost = db.Column(db.Float, default=0.0)
    upload_time = db.Column(db.DateTime, index=True, default=datetime.utcnow)
    status = db.Column(db.String(50), default='pending')
    payment_status = db.Column(db.String(50), default='unpaid')
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    payment = db.relationship('Payment', backref='job', uselist=False)

class Payment(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    job_id = db.Column(db.Integer, db.ForeignKey('print_job.id'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    amount = db.Column(db.Float, nullable=False)
    method = db.Column(db.String(50), nullable=False)
    account_name = db.Column(db.String(100), nullable=True)
    proof_filename = db.Column(db.String(255), nullable=True)
    midtrans_transaction_id = db.Column(db.String(255), nullable=True, unique=True)
    status = db.Column(db.String(50), default='pending')
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    confirmed_at = db.Column(db.DateTime, nullable=True)
    notes = db.Column(db.Text, nullable=True)

class PaymentAccount(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    method = db.Column(db.String(50), nullable=False) # e.g., 'bca', 'dana', 'midtrans'
    label = db.Column(db.String(100), nullable=False)
    account_number = db.Column(db.String(100), nullable=False)
    account_name = db.Column(db.String(100), nullable=False)
    qr_filename = db.Column(db.String(255), nullable=True)
    is_active = db.Column(db.Boolean, default=True)

class ChatMessage(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    message = db.Column(db.Text, nullable=False)
    is_from_admin = db.Column(db.Boolean, default=False)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    is_read = db.Column(db.Boolean, default=False)
    
    user = db.relationship('User', backref=db.backref('chat_messages', lazy='dynamic'))

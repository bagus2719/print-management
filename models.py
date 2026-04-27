import secrets
from datetime import datetime
from werkzeug.security import generate_password_hash, check_password_hash
from flask_login import UserMixin
from extensions import db, login_manager

class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(64), index=True, unique=True, nullable=False)
    email = db.Column(db.String(120), index=True, unique=True, nullable=False)
    password_hash = db.Column(db.String(256))
    is_admin = db.Column(db.Boolean, default=False)
    reset_token = db.Column(db.String(100), unique=True, nullable=True)
    reset_token_expiry = db.Column(db.DateTime, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    jobs = db.relationship('PrintJob', backref='author', lazy='dynamic')
    payments = db.relationship('Payment', backref='payer', lazy='dynamic')

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    def generate_reset_token(self):
        self.reset_token = secrets.token_urlsafe(32)
        self.reset_token_expiry = datetime.utcnow()
        return self.reset_token

@login_manager.user_loader
def load_user(id):
    return User.query.get(int(id))

class PrintJob(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    filename = db.Column(db.String(255), nullable=False, unique=True)
    display_name = db.Column(db.String(255), nullable=False)
    filepath = db.Column(db.String(512), nullable=False)
    pages = db.Column(db.Integer, nullable=False)
    copies = db.Column(db.Integer, default=1)
    print_type = db.Column(db.String(50), default='-')
    paper_size = db.Column(db.String(50), default='A4')
    paper_source = db.Column(db.String(50), default='dari_kami', nullable=False)
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
    status = db.Column(db.String(50), default='pending')
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    confirmed_at = db.Column(db.DateTime, nullable=True)
    notes = db.Column(db.Text, nullable=True)

class PaymentAccount(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    method = db.Column(db.String(50), nullable=False) # e.g., 'bca', 'dana', 'shopeepay'
    label = db.Column(db.String(100), nullable=False) # e.g., 'Bank BCA'
    account_number = db.Column(db.String(100), nullable=False)
    account_name = db.Column(db.String(100), nullable=False)
    qr_filename = db.Column(db.String(255), nullable=True) # for QRIS barcode image
    is_active = db.Column(db.Boolean, default=True)

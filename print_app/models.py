from datetime import datetime
from werkzeug.security import generate_password_hash, check_password_hash
from flask_login import UserMixin
from . import db, login_manager

class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(64), index=True, unique=True, nullable=False)
    email = db.Column(db.String(120), index=True, unique=True, nullable=False)
    password_hash = db.Column(db.String(256))
    is_admin = db.Column(db.Boolean, default=False)
    jobs = db.relationship('PrintJob', backref='author', lazy='dynamic')

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

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
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
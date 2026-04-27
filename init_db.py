from app import create_app
from extensions import db
from models import User, Payment, PaymentAccount

app = create_app()

with app.app_context():
    print("Menghapus database lama (jika ada)...")
    db.drop_all()
    print("Membuat tabel baru...")
    db.create_all()

    print("Membuat user admin...")
    admin = User(username='admin', email='admin@gmail.com', is_admin=True)
    admin.set_password('admin123')
    db.session.add(admin)

    print("Membuat user biasa...")
    user = User(username='bagus', email='bagustrialahmadi27@gmail.com')
    user.set_password('bagus123')
    db.session.add(user)

    print("Membuat akun pembayaran default...")
    accounts = [
        PaymentAccount(method='bca', label='Bank BCA', account_number='8162054219', account_name='Bagus Tri Al Ahmadi'),
        PaymentAccount(method='dana', label='DANA', account_number='081332090934', account_name='Bagus Tri Al Ahmadi'),
        PaymentAccount(method='shopeepay', label='ShopeePay', account_number='083111481327', account_name='Bagus Tri Al Ahmadi'),
        PaymentAccount(method='qris', label='QRIS', account_number='Bagus Tri Al Ahmadi', account_name='Bagus Tri'),
    ]
    db.session.add_all(accounts)
    
    db.session.commit()
    print("User 'admin' (pass: admin123) dan 'bagus' (pass: bagus123) berhasil dibuat.")
    print("3 akun pembayaran default berhasil dibuat (BCA, DANA, ShopeePay).")
    print("Inisialisasi database selesai.")
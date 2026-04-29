from app import create_app
from extensions import db
from models import User, Payment, PaymentAccount, PrintPricing

app = create_app()

with app.app_context():
    print("Menghapus database lama (jika ada)...")
    db.drop_all()
    print("Membuat tabel baru...")
    db.create_all()

    print("Membuat user admin...")
    admin = User(username='admin', is_admin=True)
    admin.set_password('admin123')
    db.session.add(admin)

    print("Membuat user biasa...")
    user = User(username='bagus')
    user.set_password('bagus123')
    db.session.add(user)

    print("Membuat pengaturan harga cetak...")
    pricing_config = [
        PrintPricing(setting_key='A4_BW', setting_name='A4 Hitam Putih (Dasar)', price=250.0, description='Harga dasar per halaman untuk A4 B&W'),
        PrintPricing(setting_key='A4_COLOR', setting_name='A4 Warna (Dasar)', price=300.0, description='Harga dasar per halaman untuk A4 Warna'),
        PrintPricing(setting_key='DISCOUNT_SELF', setting_name='Diskon Bawa Kertas', price=150.0, description='Potongan harga jika bawa kertas sendiri'),
        PrintPricing(setting_key='MULT_A4', setting_name='Pengali Ukuran A4', price=1.0, description='Faktor pengali untuk ukuran A4'),
        PrintPricing(setting_key='MULT_F4', setting_name='Pengali Ukuran F4', price=1.0, description='Faktor pengali untuk ukuran F4'),
        PrintPricing(setting_key='MULT_A3', setting_name='Pengali Ukuran A3', price=2.0, description='Faktor pengali untuk ukuran A3')
    ]
    db.session.add_all(pricing_config)

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
    print("Inisialisasi database selesai.")
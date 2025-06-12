from print_app import create_app, db
from print_app.models import User

app = create_app()

with app.app_context():
    print("Menghapus database lama (jika ada)...")
    db.drop_all()
    print("Membuat tabel baru...")
    db.create_all()

    print("Membuat user admin...")
    admin = User(
        username='admin',
        email='admin@example.com',
        is_admin=True
    )
    admin.set_password('admin123')
    db.session.add(admin)

    print("Membuat user biasa...")
    user = User(
        username='testuser',
        email='test@example.com'
    )
    user.set_password('user123')
    db.session.add(user)
    
    db.session.commit()
    print("User 'admin' (pass: admin123) dan 'testuser' (pass: user123) berhasil dibuat.")
    print("Inisialisasi database selesai.")
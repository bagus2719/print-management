from app import create_app
from extensions import db
from models import ChatMessage  # Pastikan model baru diimpor agar terdeteksi

app = create_app()

with app.app_context():
    print("Menambah tabel baru ke database (tanpa menghapus data lama)...")
    # db.create_all() hanya akan membuat tabel yang BELUM ADA di database.
    # Data lama Anda (User, PrintJob, dll) akan tetap aman.
    db.create_all()
    print("Berhasil! Tabel ChatMessage telah ditambahkan jika belum ada.")
    print("Database Anda sekarang up-to-date.")

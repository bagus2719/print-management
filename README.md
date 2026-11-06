# 🖨️ PrintManager

**PrintManager** adalah aplikasi web manajemen jasa cetak dokumen online berbasis Flask. Pengguna dapat mengupload dokumen, mengatur konfigurasi cetak, melakukan pembayaran, dan melacak status pesanan secara real-time.

> 🌐 **Live Demo:** [bagus2719.pythonanywhere.com](https://bagus2719.pythonanywhere.com)

---

## ✨ Fitur Utama

### 👤 Sisi Pengguna
- **Upload Multi-File** — Upload PDF, Word (.docx), PowerPoint (.pptx), Excel (.xlsx), dan gambar sekaligus
- **Auto Page Detection** — Jumlah halaman terdeteksi otomatis untuk PDF dan file Office
- **Konfigurasi Cetak** — Pilih warna (B&W/Color), ukuran kertas (A4/F4/A3), jumlah copy, duplex, dan sumber kertas
- **Kalkulasi Harga Otomatis** — Harga dihitung secara dinamis berdasarkan konfigurasi
- **Multi-Payment Gateway** — Pembayaran via Midtrans (GoPay, QRIS, VA Bank), transfer manual, dan cash
- **Riwayat Pesanan** — Lihat semua pesanan dengan sorting dan tracking status
- **Live Chat** — Chat langsung dengan admin dari dalam aplikasi
- **Dark Mode** — Tampilan gelap yang nyaman di mata

### 🔧 Sisi Admin
- **Dashboard** — Ringkasan total pesanan, pengguna, pendapatan, dan pembayaran pending
- **Kelola Pesanan** — Update status (pending → printing → completed), filter, sorting, dan bulk delete
- **Kelola Pengguna** — Lihat daftar user, toggle admin, reset password, dan hapus user
- **Kelola Pembayaran** — Konfirmasi/tolak pembayaran manual, set status pembayaran
- **Kelola Akun Pembayaran** — Tambah/edit rekening bank, e-wallet, dan QRIS untuk ditampilkan ke user
- **Live Chat** — Balas pesan dari pengguna dengan auto-cleanup pesan > 7 hari

---

## 🛠️ Tech Stack

| Layer | Teknologi |
|-------|-----------|
| **Backend** | Python, Flask |
| **Database** | SQLite (via SQLAlchemy ORM) |
| **Auth** | Flask-Login, Werkzeug (password hashing) |
| **Payment** | Midtrans Snap API |
| **Frontend** | Tailwind CSS (CDN), Font Awesome, Plus Jakarta Sans |
| **Deployment** | PythonAnywhere |

---

## 📁 Struktur Proyek

```
print-management/
├── app.py                  # Flask app factory
├── main.py                 # Route utama (upload, configure, payment, chat)
├── admin.py                # Route admin panel
├── auth.py                 # Route autentikasi (login, register, logout)
├── models.py               # Database models (User, PrintJob, Payment, dll.)
├── config.py               # Konfigurasi app (env vars, upload settings)
├── extensions.py           # Inisialisasi extensions (db, login, csrf)
├── init_db.py              # Script inisialisasi database + seed data
├── update_db.py            # Script update schema (non-destructive)
├── migrate_pythonanywhere.py  # Script migrasi untuk PythonAnywhere
├── wsgi.py                 # WSGI entry point untuk PythonAnywhere
├── requirements.txt        # Dependency Python
├── .env                    # Environment variables (tidak di-commit)
├── .gitignore
├── static/
│   ├── css/style.css       # Custom CSS (complement Tailwind)
│   └── js/script.js        # Minimal JavaScript
├── templates/
│   ├── layouts/            # Base templates (app.html, admin.html)
│   ├── auth/               # Login & register pages
│   ├── user/               # Dashboard, history, configure, payment, profile
│   ├── admin/              # Admin dashboard, jobs, users, payments, chats
│   └── pages/              # Terms, privacy, refund (Midtrans KYC)
├── uploads/                # File yang diupload user (tidak di-commit)
└── instance/               # SQLite database (tidak di-commit)
```

---

## 🚀 Instalasi & Setup Lokal

### Prasyarat
- Python 3.10+
- pip

### Langkah-langkah

1. **Clone repository**
   ```bash
   git clone https://github.com/bagus2719/print-management.git
   cd print-management
   ```

2. **Buat virtual environment**
   ```bash
   python -m venv venv

   # Windows
   venv\Scripts\activate

   # Linux/Mac
   source venv/bin/activate
   ```

3. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

4. **Konfigurasi environment variables**

   Buat file `.env` di root project:
   ```env
   SECRET_KEY=your-secret-key-here
   WTF_CSRF_SECRET_KEY=your-csrf-secret-key-here

   # Midtrans (opsional, untuk payment gateway)
   MIDTRANS_MERCHANT_ID=your-merchant-id
   MIDTRANS_CLIENT_KEY=your-client-key
   MIDTRANS_SERVER_KEY=your-server-key
   MIDTRANS_IS_PRODUCTION=false
   ```

   > 💡 Generate secret key: `python -c "import secrets; print(secrets.token_hex(32))"`

5. **Inisialisasi database**
   ```bash
   python init_db.py
   ```
   Ini akan membuat database dengan user default:
   - Admin: `admin` / `admin123`
   - User: `bagus` / `bagus123`

   > ⚠️ **Ganti password default setelah login pertama!**

6. **Jalankan aplikasi**
   ```bash
   python app.py
   ```
   Buka http://localhost:5000 di browser.

---

## ☁️ Deployment ke PythonAnywhere

1. Upload/clone project ke PythonAnywhere
2. Buat virtualenv dan install dependencies:
   ```bash
   mkvirtualenv --python=/usr/bin/python3.10 venv
   pip install -r requirements.txt
   ```
3. Set **Source code** dan **Virtualenv** path di tab Web
4. Edit WSGI configuration file sesuai isi `wsgi.py`
5. Set environment variables di `.env`
6. Jalankan migrasi:
   ```bash
   python migrate_pythonanywhere.py
   ```
7. Klik **Reload** di tab Web

---

## 💳 Konfigurasi Midtrans

1. Daftar di [Midtrans Dashboard](https://dashboard.midtrans.com)
2. Dapatkan `Merchant ID`, `Client Key`, dan `Server Key`
3. Masukkan ke file `.env`
4. Set Notification URL (webhook) di Midtrans Dashboard:
   ```
   https://your-domain.com/midtrans_webhook
   ```
5. Untuk production, set `MIDTRANS_IS_PRODUCTION=true`

---

## 📸 Screenshots

| Halaman | Deskripsi |
|---------|-----------|
| Dashboard User | Upload file dan lihat pesanan terbaru |
| Konfigurasi Cetak | Atur detail cetak per file (warna, ukuran, copy) |
| Pembayaran | Pilih metode bayar (Midtrans/Transfer/Cash) |
| Admin Dashboard | Statistik dan overview seluruh sistem |
| Admin - Kelola Pesanan | Filter, sort, update status, download file |

---

## 📄 Lisensi

Project ini dibuat untuk keperluan pribadi / tugas.

---

## 👤 Kontak

- **Nama:** Bagus Tri Al Ahmadi
- **Email:** bagustrialahmadi27@gmail.com
- **WhatsApp:** [081332090934](https://wa.me/6281332090934)


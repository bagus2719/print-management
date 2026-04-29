import sqlite3
import os

# Path database di PythonAnywhere (folder instance)
db_path = 'instance/print_jobs.db'

def migrate():
    target_db = db_path
    
    if not os.path.exists(target_db):
        # Coba path alternatif jika instance tidak ditemukan
        alt_path = 'db_pythonanywhere/print_jobs.db'
        if os.path.exists(alt_path):
            target_db = alt_path
        else:
            print(f"File database tidak ditemukan di '{db_path}' maupun '{alt_path}'!")
            return

    conn = sqlite3.connect(target_db)
    cursor = conn.cursor()

    print(f"Memulai migrasi database: {target_db}...")

    # 1. Tambah kolom ke tabel payment
    columns_to_add = [
        ("midtrans_transaction_id", "VARCHAR(255)"),
        ("confirmed_at", "DATETIME"),
        ("notes", "TEXT"),
        ("account_name", "VARCHAR(100)")
    ]
    
    for col_name, col_type in columns_to_add:
        try:
            cursor.execute(f"ALTER TABLE payment ADD COLUMN {col_name} {col_type}")
            print(f"- Kolom '{col_name}' ditambahkan ke tabel 'payment'")
        except sqlite3.OperationalError:
            print(f"- Kolom '{col_name}' sudah ada.")

    # 2. Tambah kolom ke tabel print_job
    try:
        cursor.execute("ALTER TABLE print_job ADD COLUMN color_mode VARCHAR(50) DEFAULT 'bw'")
        cursor.execute("ALTER TABLE print_job ADD COLUMN is_duplex BOOLEAN DEFAULT 0")
        print("- Kolom 'color_mode' dan 'is_duplex' ditambahkan ke tabel 'print_job'")
    except sqlite3.OperationalError:
        print("- Kolom di 'print_job' sudah ada.")

    # 3. Buat tabel print_pricing
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS print_pricing (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        setting_key VARCHAR(50) UNIQUE NOT NULL,
        setting_name VARCHAR(100) NOT NULL,
        price FLOAT NOT NULL,
        description VARCHAR(255)
    )
    """)
    print("- Tabel 'print_pricing' dipastikan ada.")

    # 4. Buat tabel chat_message
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS chat_message (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        message TEXT NOT NULL,
        is_from_admin BOOLEAN DEFAULT 0,
        timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
        is_read BOOLEAN DEFAULT 0,
        FOREIGN KEY(user_id) REFERENCES user(id)
    )
    """)
    print("- Tabel 'chat_message' dipastikan ada.")

    # 5. Buat tabel payment_account
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS payment_account (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        method VARCHAR(50) NOT NULL,
        label VARCHAR(100) NOT NULL,
        account_number VARCHAR(100) NOT NULL,
        account_name VARCHAR(100) NOT NULL,
        qr_filename VARCHAR(255),
        is_active BOOLEAN DEFAULT 1
    )
    """)
    print("- Tabel 'payment_account' dipastikan ada.")

    # 6. Isi data default pricing jika kosong
    cursor.execute("SELECT COUNT(*) FROM print_pricing")
    if cursor.fetchone()[0] == 0:
        pricing = [
            ('A4_BW', 'A4 Hitam Putih (Dasar)', 500.0),
            ('A4_COLOR', 'A4 Warna (Dasar)', 2000.0),
            ('DISCOUNT_SELF', 'Diskon Bawa Kertas', 100.0),
            ('MULT_A4', 'Pengali Ukuran A4', 1.0),
            ('MULT_F4', 'Pengali Ukuran F4', 1.1),
            ('MULT_A3', 'Pengali Ukuran A3', 2.0)
        ]
        cursor.executemany("INSERT INTO print_pricing (setting_key, setting_name, price) VALUES (?, ?, ?)", pricing)
        print("- Data default pricing berhasil ditambahkan.")

    conn.commit()
    conn.close()
    print("\nMigrasi selesai! Database sekarang kompatibel dengan kode terbaru.")
    print("Silakan RELOAD web app Anda di Dashboard PythonAnywhere.")

if __name__ == "__main__":
    migrate()

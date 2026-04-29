import sqlite3
import os

db_path = 'db_pythonanywhere/print_jobs.db'

def migrate():
    if not os.path.exists(db_path):
        print(f"File {db_path} tidak ditemukan!")
        return

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    print("Memulai migrasi database PythonAnywhere...")

    # 1. Tambah kolom ke tabel payment
    try:
        cursor.execute("ALTER TABLE payment ADD COLUMN midtrans_transaction_id VARCHAR(255)")
        print("- Kolom 'midtrans_transaction_id' ditambahkan ke tabel 'payment'")
    except sqlite3.OperationalError:
        print("- Kolom 'midtrans_transaction_id' sudah ada.")

    # 2. Tambah kolom ke tabel print_job
    try:
        cursor.execute("ALTER TABLE print_job ADD COLUMN color_mode VARCHAR(50) DEFAULT 'bw'")
        cursor.execute("ALTER TABLE print_job ADD COLUMN is_duplex BOOLEAN DEFAULT 0")
        # Pindahkan data dari print_type ke color_mode jika perlu
        cursor.execute("UPDATE print_job SET color_mode = print_type WHERE print_type IS NOT NULL")
        print("- Kolom 'color_mode' dan 'is_duplex' ditambahkan ke tabel 'print_job'")
    except sqlite3.OperationalError:
        print("- Kolom di 'print_job' sudah ada atau tabel berbeda.")

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

    # 5. Isi data default pricing jika kosong
    cursor.execute("SELECT COUNT(*) FROM print_pricing")
    if cursor.fetchone()[0] == 0:
        pricing = [
            ('A4_BW', 'A4 Hitam Putih (Dasar)', 250.0),
            ('A4_COLOR', 'A4 Warna (Dasar)', 300.0),
            ('DISCOUNT_SELF', 'Diskon Bawa Kertas', 150.0),
            ('MULT_A4', 'Pengali Ukuran A4', 1.0),
            ('MULT_F4', 'Pengali Ukuran F4', 1.0),
            ('MULT_A3', 'Pengali Ukuran A3', 2.0)
        ]
        cursor.executemany("INSERT INTO print_pricing (setting_key, setting_name, price) VALUES (?, ?, ?)", pricing)
        print("- Data default pricing berhasil ditambahkan.")

    conn.commit()
    conn.close()
    print("Migrasi selesai! Database sekarang kompatibel dengan kode terbaru.")

if __name__ == "__main__":
    migrate()

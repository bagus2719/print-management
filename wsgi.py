# ===================================================================
# PythonAnywhere WSGI Configuration
# ===================================================================
# Cara pakai di PythonAnywhere:
# 1. Di tab "Web", set Source code ke path project Anda
#    contoh: /home/bagus2719/print-management
# 2. Di WSGI configuration file, ganti isinya dengan konten ini
#    (sesuaikan path di bawah dengan username PythonAnywhere Anda)
# 3. Set virtualenv jika menggunakan venv
# ===================================================================

import sys
import os
from dotenv import load_dotenv

# Ganti 'bagus2719' dengan username PythonAnywhere Anda jika berbeda
project_home = '/home/bagus2719/print-management'

if project_home not in sys.path:
    sys.path.insert(0, project_home)

# Load environment variables dari file .env di direktori proyek
env_path = os.path.join(project_home, '.env')
if os.path.exists(env_path):
    load_dotenv(env_path)

# Set konfigurasi default production jika belum ada di environment
os.environ.setdefault('FLASK_DEBUG', 'false')

from app import app as application  # noqa

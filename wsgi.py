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

# Ganti 'bagus2719' dengan username PythonAnywhere Anda
project_home = '/home/bagus2719/print-management'

if project_home not in sys.path:
    sys.path.insert(0, project_home)

# Set environment variables untuk production
os.environ['SECRET_KEY'] = 'GANTI-DENGAN-SECRET-KEY-YANG-KUAT-DAN-PANJANG'
os.environ['FLASK_DEBUG'] = 'false'

from app import app as application  # noqa

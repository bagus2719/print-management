import os
import logging
from logging.handlers import RotatingFileHandler
from flask import Flask
from config import Config
from extensions import db, login_manager, migrate, csrf

def setup_logging(app):
    """Konfigurasi logging terstruktur untuk production troubleshooting."""
    logs_dir = os.path.join(app.instance_path, 'logs')
    os.makedirs(logs_dir, exist_ok=True)
    
    file_handler = RotatingFileHandler(
        os.path.join(logs_dir, 'printmanager.log'),
        maxBytes=2 * 1024 * 1024,  # Rotasi setiap 2 MB
        backupCount=5,
        encoding='utf-8'
    )
    file_handler.setFormatter(logging.Formatter(
        '[%(asctime)s] %(levelname)s in %(module)s (%(pathname)s:%(lineno)d): %(message)s'
    ))
    file_handler.setLevel(logging.INFO)
    app.logger.addHandler(file_handler)
    app.logger.setLevel(logging.INFO)
    app.logger.info('PrintManager application initialized.')

def create_app(config_class=Config):
    app = Flask(__name__, instance_relative_config=True)
    app.config.from_object(config_class)

    try:
        os.makedirs(app.instance_path)
    except OSError:
        pass

    setup_logging(app)

    db.init_app(app)
    login_manager.init_app(app)
    migrate.init_app(app, db)
    csrf.init_app(app)

    import auth, main, admin
    app.register_blueprint(auth.bp)
    app.register_blueprint(main.bp)
    app.register_blueprint(admin.bp)

    return app

app = create_app()

if __name__ == '__main__':
    # debug=True hanya untuk development lokal
    app.run(debug=os.environ.get('FLASK_DEBUG', 'false').lower() == 'true', host='0.0.0.0', port=5000)

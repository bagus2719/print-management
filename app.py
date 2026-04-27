import os
from flask import Flask
from config import Config
from extensions import db, login_manager, migrate

def create_app(config_class=Config):
    app = Flask(__name__, instance_relative_config=True)
    app.config.from_object(config_class)

    try:
        os.makedirs(app.instance_path)
    except OSError:
        pass

    db.init_app(app)
    login_manager.init_app(app)
    migrate.init_app(app, db)

    import auth, main, admin
    app.register_blueprint(auth.bp)
    app.register_blueprint(main.bp)
    app.register_blueprint(admin.bp)

    return app

app = create_app()

if __name__ == '__main__':
    # debug=True hanya untuk development lokal
    app.run(debug=os.environ.get('FLASK_DEBUG', 'false').lower() == 'true')

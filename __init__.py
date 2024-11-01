from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager
from controllers.config import Config

db = SQLAlchemy()
login_manager = LoginManager()

def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)

    db.init_app(app)
    login_manager.init_app(app)
    login_manager.login_view = 'main.login'

    with app.app_context():
        from controllers import routes
        app.register_blueprint(routes.main)
        db.create_all()

    return app
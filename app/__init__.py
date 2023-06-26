from flask import Flask
from flask_login import LoginManager
from app.models import db, User
from app.routes import main_blueprint
from config import Config


def create_app():
    app = Flask(__name__)

    # Configuration settings
    # app.config.from_object("config.Config")
    app.config.from_object(Config)

    # Initialize the database
    db.init_app(app)

    # Initialize login manager
    login_manager = LoginManager()
    login_manager.init_app(app)
    login_manager.login_view = "main.login"

    @login_manager.user_loader
    def load_user(user_id):
        return User.query.get(int(user_id))

    # Register routes
    app.register_blueprint(main_blueprint)

    return app

from flask import Flask
from config import Config

def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)
    
    # Register blueprints or routes
    from app.routes import main as main_blueprint
    app.register_blueprint(main_blueprint)
    
    return app

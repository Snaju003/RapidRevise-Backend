from flask import Flask
from config import Config

def create_app(config_class=Config):
    app = Flask(__name__)
    app.config.from_object(config_class)

    # Initialize extensions here if needed
    
    # Register blueprints
    from app.auth.routes import auth_bp
    from app.community.routes import community_bp
    from app.main.routes import main_bp
    from app.resources import resources_bp
    
    app.register_blueprint(auth_bp, url_prefix='/auth')
    app.register_blueprint(community_bp, url_prefix='/community')
    app.register_blueprint(resources_bp, url_prefix='/resources')
    app.register_blueprint(main_bp)
    
    return app
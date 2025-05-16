from flask import Flask, request, g
from dotenv import load_dotenv
import os

def create_app():
    app = Flask(__name__,
                static_folder='static',
                template_folder='templates')

    # Load environment variables
    load_dotenv()

    # Configure app
    app.config['SECRET_KEY'] = os.getenv('FLASK_SECRET_KEY', 'dev-key-change-this')
    app.config['LANGUAGES'] = ['en', 'uz', 'ru']
    app.config['DEFAULT_LANGUAGE'] = os.getenv('DEFAULT_LANGUAGE', 'en')
    
    # Handle language selection
    @app.before_request
    def before_request():
        # Check for language in cookies first
        lang = request.cookies.get('language')
        
        # If not found in cookies, use browser preferred language
        if not lang:
            lang = request.accept_languages.best_match(app.config['LANGUAGES'])
            
        # Default to English if no preference found
        if not lang:
            lang = app.config['DEFAULT_LANGUAGE']
            
        g.locale = lang
    
    # Create translation helper
    from app.translations import get_translation
    @app.context_processor
    def utility_processor():
        def translate(key):
            return get_translation(key, g.locale)
        return {'_': translate}

    # Register blueprints
    from .routes import bp as main_bp
    app.register_blueprint(main_bp)

    return app
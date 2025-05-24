from flask import Flask, request, session
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_login import LoginManager
from flask_babel import Babel, gettext as _ # Import gettext for potential direct use if needed
from config import Config
from datetime import datetime # Import datetime

app = Flask(__name__)
app.config.from_object(Config)
db = SQLAlchemy(app)
migrate = Migrate(app, db)
login = LoginManager(app)
login.login_view = 'login'

def get_locale():
    lang_from_session = session.get('lang')
    print(f"[DEBUG] lang from session: {lang_from_session}")
    if lang_from_session in app.config['LANGUAGES']:
        print(f"[DEBUG] Using lang from session: {lang_from_session}")
        return lang_from_session

    lang_from_args = request.args.get('lang')
    print(f"[DEBUG] lang from request.args: {lang_from_args}")
    if lang_from_args in app.config['LANGUAGES']:
        session['lang'] = lang_from_args
        print(f"[DEBUG] Using lang from request.args, setting session: {lang_from_args}")
        return lang_from_args

    best_match_lang = request.accept_languages.best_match(app.config['LANGUAGES'])
    print(f"[DEBUG] lang from accept_languages: {best_match_lang}")
    if best_match_lang:
        # Optionally set it to session if you want accept_languages to persist for the session
        # session['lang'] = best_match_lang 
        print(f"[DEBUG] Using lang from accept_languages: {best_match_lang}")
        return best_match_lang
    
    default_lang = app.config['BABEL_DEFAULT_LOCALE']
    print(f"[DEBUG] Falling back to default locale: {default_lang}")
    return default_lang

babel = Babel(app, locale_selector=get_locale)

@app.context_processor
def inject_now_utc():
    return {'now_utc': datetime.utcnow()}

from app import routes, models

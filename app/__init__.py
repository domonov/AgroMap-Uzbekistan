from flask import Flask, request
from flask_sqlalchemy import SQLAlchemy
from flask_compress import Compress
from flask_assets import Environment, Bundle
from sqlalchemy import event
from sqlalchemy.engine import Engine
import os
import logging
from logging.handlers import RotatingFileHandler
import time
import sentry_sdk
from sentry_sdk.integrations.flask import FlaskIntegration
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Initialize extensions
db = SQLAlchemy()
compress = Compress()
assets = Environment()

# Import core utilities
from app.utils.performance import PerformanceOptimizer
from app.utils.performance_monitor import PerformanceMonitor
from app.utils.asset_optimizer import AssetOptimizer
from app.utils.js_optimizer import JSOptimizer

# Import security utilities 
from app.security import init_security, csrf, limiter

# Import maintenance utilities
from app.utils.db_maintenance import init_db_maintenance
from app.utils.code_cleaner import CodeOptimizer
from app.utils.final_optimizer import init_final_optimizer

# Import monitoring utilities
from app.utils.monitoring import MonitoringSystem

# Cache middleware
from app.cache import CacheMiddleware

def create_app():
    app = Flask(__name__)

    # Initialize Sentry for error tracking
    if os.environ.get("SENTRY_DSN"):
        sentry_sdk.init(
            dsn=os.environ.get("SENTRY_DSN"),
            integrations=[FlaskIntegration()],
            traces_sample_rate=1.0,
            environment=os.environ.get("FLASK_ENV", "production")
        )

    # App Configuration
    app.config["SQLALCHEMY_DATABASE_URI"] = os.environ.get(
        "DATABASE_URL", 
        "postgresql://username:password@localhost:5432/agromap"
    )
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

    # Security Configuration
    app.config["SECRET_KEY"] = os.environ.get("SECRET_KEY")
    app.config["WTF_CSRF_SECRET_KEY"] = os.environ.get("WTF_CSRF_SECRET_KEY")
    app.config["WTF_CSRF_TIME_LIMIT"] = 3600  # CSRF token expiry in seconds
    app.config["PERMANENT_SESSION_LIFETIME"] = 3600  # Session lifetime in seconds

    # Session security
    app.config["SESSION_COOKIE_SECURE"] = os.environ.get("SESSION_COOKIE_SECURE", "True").lower() == "true"
    app.config["SESSION_COOKIE_HTTPONLY"] = os.environ.get("SESSION_COOKIE_HTTPONLY", "True").lower() == "true"
    app.config["SESSION_COOKIE_SAMESITE"] = os.environ.get("SESSION_COOKIE_SAMESITE", "Strict")

    # Rate limiting configuration
    app.config["RATELIMIT_STORAGE_URL"] = os.environ.get("RATELIMIT_STORAGE_URL", "memory://")
    app.config["RATELIMIT_STRATEGY"] = "fixed-window"
    app.config["RATELIMIT_DEFAULT"] = os.environ.get("RATELIMIT_DEFAULT", "200 per day;50 per hour")

    # API Security
    app.config["API_KEY_HEADER_NAME"] = os.environ.get("API_KEY_HEADER_NAME", "X-API-Key")
    app.config["API_KEY_EXPIRY_DAYS"] = int(os.environ.get("API_KEY_EXPIRY_DAYS", "30"))

    # Initialize database
    db.init_app(app)

    # Initialize monitoring system
    app.config['METRICS_PORT'] = int(os.environ.get('METRICS_PORT', 9090))
    app.config['DATADOG_API_KEY'] = os.environ.get('DATADOG_API_KEY')
    app.config['DATADOG_APP_KEY'] = os.environ.get('DATADOG_APP_KEY')

    monitoring_system = MonitoringSystem()
    monitoring_system.init_app(app)

    # Initialize optimizers and monitors
    performance_optimizer = PerformanceOptimizer()
    performance_optimizer.init_app(app)

    performance_monitor = PerformanceMonitor()
    performance_monitor.init_app(app)

    # Initialize security features
    init_security(app)

    # Initialize code optimizer
    code_optimizer = CodeOptimizer(os.path.dirname(__file__))
    code_optimizer.init_app(app)

    # Initialize database maintenance
    init_db_maintenance(app, db)

    # Initialize final optimizer
    init_final_optimizer(app, db)

    # Configure compression
    compress.init_app(app)
    app.config['COMPRESS_MIMETYPES'] = [
        'text/html',
        'text/css',
        'text/xml',
        'application/json',
        'application/javascript',
        'text/javascript',
        'application/x-javascript'
    ]
    app.config['COMPRESS_LEVEL'] = 6
    app.config['COMPRESS_MIN_SIZE'] = 500

    # Configure static file serving
    app.config['SEND_FILE_MAX_AGE_DEFAULT'] = 31536000  # 1 year

    # Configure assets
    assets.init_app(app)

    # Create and register asset bundles
    js_bundle = Bundle(
        'js/app.js',
        'js/map-touch.js',
        filters='jsmin',
        output='dist/js/bundle.%(version)s.js'
    )

    css_bundle = Bundle(
        'css/map.css',
        'css/responsive.css',
        filters='cssmin',
        output='dist/css/bundle.%(version)s.css'
    )

    assets.register('js_all', js_bundle)
    assets.register('css_all', css_bundle)

    # Create cache directories
    cache_dir = os.path.join(app.instance_path, 'cache')
    static_cache_dir = os.path.join(app.static_folder, 'dist')
    os.makedirs(cache_dir, exist_ok=True)
    os.makedirs(static_cache_dir, exist_ok=True)

    # Import and register routes
    from app.routes import main_bp
    app.register_blueprint(main_bp)

    return app

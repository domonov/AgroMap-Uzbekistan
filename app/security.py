"""Security utilities for AgroMap."""
from functools import wraps
from flask import request, abort, current_app
from flask_wtf.csrf import CSRFProtect
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
import re
import bleach
from urllib.parse import urlparse
import ipaddress
from wtforms.validators import ValidationError
from . import logging

csrf = CSRFProtect()
limiter = Limiter(
    key_func=get_remote_address,
    default_limits=["200 per day", "50 per hour"]
)

def init_security(app):
    """Initialize security features."""
    # Initialize CSRF protection
    csrf.init_app(app)
    
    # Initialize rate limiting
    limiter.init_app(app)
    
    # Initialize logging
    logging.setup_logging(app)
    
    # Configure security headers
    @app.after_request
    def add_security_headers(response):
        response.headers['X-Content-Type-Options'] = 'nosniff'
        response.headers['X-Frame-Options'] = 'SAMEORIGIN'
        response.headers['X-XSS-Protection'] = '1; mode=block'
        response.headers['Content-Security-Policy'] = get_content_security_policy()
        response.headers['Strict-Transport-Security'] = 'max-age=31536000; includeSubDomains'
        response.headers['Referrer-Policy'] = 'strict-origin-when-cross-origin'
        return response

    # Log failed login attempts
    @app.after_request
    def log_failed_logins(response):
        if (request.endpoint == 'auth.login' and 
            request.method == 'POST' and 
            response.status_code != 200):
            logging.log_security_event(
                app,
                'failed_login',
                'Failed login attempt',
                ip=request.remote_addr
            )
        return response

    # Log unauthorized access attempts
    @app.after_request
    def log_unauthorized(response):
        if response.status_code in [401, 403]:
            logging.log_security_event(
                app,
                'unauthorized_access',
                f'Unauthorized access attempt to {request.path}',
                ip=request.remote_addr
            )
        return response

def get_content_security_policy():
    """Get Content Security Policy header value."""
    return "; ".join([
        "default-src 'self'",
        "img-src 'self' data: https: blob:",
        "script-src 'self' 'unsafe-inline' 'unsafe-eval' https://unpkg.com https://cdn.jsdelivr.net",
        "style-src 'self' 'unsafe-inline' https://unpkg.com",
        "font-src 'self'",
        "connect-src 'self' https://api.openweathermap.org",
        "frame-ancestors 'none'",
        "form-action 'self'",
        "base-uri 'self'",
        "object-src 'none'"
    ])

def sanitize_input(data):
    """Sanitize user input to prevent XSS attacks."""
    if isinstance(data, str):
        return bleach.clean(data, tags=[], strip=True)
    elif isinstance(data, dict):
        return {k: sanitize_input(v) for k, v in data.items()}
    elif isinstance(data, list):
        return [sanitize_input(i) for i in data]
    return data

def validate_url(url):
    """Validate and sanitize URLs."""
    try:
        parsed = urlparse(url)
        if not parsed.scheme or not parsed.netloc:
            return False
        if parsed.scheme not in ['http', 'https']:
            return False
        return True
    except:
        return False

def validate_ip(ip):
    """Validate IP addresses."""
    try:
        ipaddress.ip_address(ip)
        return True
    except:
        return False

def validate_coordinates(lat, lon):
    """Validate geographic coordinates."""
    try:
        lat = float(lat)
        lon = float(lon)
        return -90 <= lat <= 90 and -180 <= lon <= 180
    except:
        return False

def require_api_key(f):
    """Decorator to require API key for routes."""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        api_key = request.headers.get('X-API-Key')
        if not api_key or not validate_api_key(api_key):
            abort(401, description="Invalid or missing API key")
        return f(*args, **kwargs)
    return decorated_function

def api_rate_limit():
    """Rate limiting decorator for API endpoints."""
    def decorator(f):
        @limiter.limit("100/hour")  # Stricter limit for API endpoints
        @wraps(f)
        def wrapped(*args, **kwargs):
            return f(*args, **kwargs)
        return wrapped
    return decorator

class FormValidation:
    """Form validation utilities."""
    
    @staticmethod
    def validate_password(form, field):
        """Validate password strength."""
        password = field.data
        if len(password) < 8:
            raise ValidationError('Password must be at least 8 characters long')
        if not re.search(r'[A-Z]', password):
            raise ValidationError('Password must contain at least one uppercase letter')
        if not re.search(r'[a-z]', password):
            raise ValidationError('Password must contain at least one lowercase letter')
        if not re.search(r'\d', password):
            raise ValidationError('Password must contain at least one number')
        if not re.search(r'[!@#$%^&*(),.?":{}|<>]', password):
            raise ValidationError('Password must contain at least one special character')
    
    @staticmethod
    def validate_username(form, field):
        """Validate username format."""
        username = field.data
        if not re.match(r'^[a-zA-Z0-9_-]{3,32}$', username):
            raise ValidationError('Username must be 3-32 characters and contain only letters, numbers, underscore, and hyphen')
    
    @staticmethod
    def validate_email(form, field):
        """Validate email format."""
        email = field.data
        if not re.match(r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$', email):
            raise ValidationError('Invalid email format')

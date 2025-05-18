"""Error tracking and handling utilities."""
import sentry_sdk
from flask import current_app
from functools import wraps
from typing import Optional, Callable, Dict, Any
import traceback
import time
from app.logging import log_error

def track_error(func: Callable) -> Callable:
    """Decorator to track errors in functions."""
    @wraps(func)
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except Exception as e:
            # Get the error context
            error_context = {
                'function': func.__name__,
                'args': args,
                'kwargs': kwargs,
                'timestamp': time.time(),
                'traceback': traceback.format_exc()
            }
            
            # Log the error locally
            log_error(current_app, e, context=error_context)
            
            # Send to Sentry if configured
            if hasattr(current_app, 'config') and current_app.config.get('SENTRY_DSN'):
                with sentry_sdk.push_scope() as scope:
                    scope.set_context("error_info", error_context)
                    sentry_sdk.capture_exception(e)
            
            # Re-raise the exception
            raise
    return wrapper

def handle_api_error(error: Exception) -> Dict[str, Any]:
    """Handle API errors and return appropriate response."""
    error_id = str(int(time.time()))
    
    # Log the error
    log_error(current_app, error, context={'error_id': error_id})
    
    # Send to Sentry if configured
    if hasattr(current_app, 'config') and current_app.config.get('SENTRY_DSN'):
        with sentry_sdk.push_scope() as scope:
            scope.set_tag("error_id", error_id)
            sentry_sdk.capture_exception(error)
    
    # Determine the error type and appropriate response
    if isinstance(error, ValueError):
        status_code = 400
        error_type = "ValidationError"
    elif isinstance(error, PermissionError):
        status_code = 403
        error_type = "PermissionDenied"
    elif isinstance(error, KeyError):
        status_code = 404
        error_type = "NotFound"
    else:
        status_code = 500
        error_type = "InternalServerError"
    
    return {
        'error': {
            'type': error_type,
            'message': str(error),
            'id': error_id
        }
    }, status_code

def setup_error_handlers(app):
    """Setup error handlers for the application."""
    
    @app.errorhandler(400)
    def bad_request_error(error):
        return handle_api_error(error)
    
    @app.errorhandler(401)
    def unauthorized_error(error):
        return handle_api_error(error)
    
    @app.errorhandler(403)
    def forbidden_error(error):
        return handle_api_error(error)
    
    @app.errorhandler(404)
    def not_found_error(error):
        return handle_api_error(error)
    
    @app.errorhandler(429)
    def ratelimit_error(error):
        return handle_api_error(error)
    
    @app.errorhandler(500)
    def internal_error(error):
        return handle_api_error(error)
    
    @app.errorhandler(Exception)
    def unhandled_exception(error):
        return handle_api_error(error)

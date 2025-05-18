"""Logging configuration for AgroMap."""
import logging
import os
from logging.handlers import RotatingFileHandler
from datetime import datetime

def setup_logging(app):
    """Configure logging for the application."""
    # Ensure logs directory exists
    if not os.path.exists('logs'):
        os.makedirs('logs')

    # Create formatters and handlers
    formatter = logging.Formatter(
        '[%(asctime)s] %(levelname)s in %(module)s: %(message)s'
    )

    # Security events log
    security_handler = RotatingFileHandler(
        'logs/security.log',
        maxBytes=10485760,  # 10MB
        backupCount=10
    )
    security_handler.setLevel(logging.INFO)
    security_handler.setFormatter(formatter)

    # Error log
    error_handler = RotatingFileHandler(
        'logs/error.log',
        maxBytes=10485760,  # 10MB
        backupCount=10
    )
    error_handler.setLevel(logging.ERROR)
    error_handler.setFormatter(formatter)

    # Setup security logger
    security_logger = logging.getLogger('security')
    security_logger.setLevel(logging.INFO)
    security_logger.addHandler(security_handler)

    # Setup error logger
    error_logger = logging.getLogger('error')
    error_logger.setLevel(logging.ERROR)
    error_logger.addHandler(error_handler)

    # Register loggers with app
    app.security_logger = security_logger
    app.error_logger = error_logger

    # Log startup
    security_logger.info('Application security logging initialized')
    
def log_security_event(app, event_type, details, ip=None, user_id=None):
    """Log a security event."""
    message = f"Security Event: {event_type} - "
    if user_id:
        message += f"User: {user_id} - "
    if ip:
        message += f"IP: {ip} - "
    message += f"Details: {details}"
    app.security_logger.info(message)

def log_error(app, error, context=None):
    """Log an error event."""
    message = f"Error: {str(error)}"
    if context:
        message += f" - Context: {context}"
    app.error_logger.error(message)

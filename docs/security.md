# Security Implementation Guide

## Overview
This document outlines the security measures implemented in the AgroMap application.

## Features

### 1. CSRF Protection
- CSRF tokens required for all forms
- Token rotation every hour
- Secure token validation

### 2. Rate Limiting
- Default limits: 200 requests per day, 50 per hour
- Stricter API endpoint limits: 100 requests per hour
- Redis-based rate limiting in production

### 3. Input Validation
- Form validation with WTForms
- Input sanitization for XSS prevention
- URL and IP address validation
- Geographic coordinate validation

### 4. Session Security
- Secure session configuration
- HTTP-only cookies
- Same-site cookie policy
- Session timeout after 1 hour

### 5. API Security
- API key authentication
- Key rotation and expiry
- Rate limiting for API endpoints
- Input validation for all endpoints

### 6. Error Tracking
- Sentry integration for error monitoring
- Structured error logging
- Error context capture
- Custom error handlers

### 7. Secure Headers
- Content Security Policy (CSP)
- X-Content-Type-Options
- X-Frame-Options
- X-XSS-Protection
- HSTS (HTTP Strict Transport Security)
- Referrer Policy

## Configuration

### Environment Variables
Create a `.env` file based on `.env.example` with the following variables:
```
SECRET_KEY=your-secret-key
WTF_CSRF_SECRET_KEY=your-csrf-secret-key
JWT_SECRET_KEY=your-jwt-secret-key
RATELIMIT_DEFAULT="200 per day;50 per hour"
RATELIMIT_STORAGE_URL="redis://localhost:6379/0"
SESSION_COOKIE_SECURE=True
SESSION_COOKIE_HTTPONLY=True
SESSION_COOKIE_SAMESITE=Strict
API_KEY_HEADER_NAME=X-API-Key
API_KEY_EXPIRY_DAYS=30
SENTRY_DSN=your-sentry-dsn
```

### Production Checklist
1. Set strong secret keys
2. Enable HTTPS
3. Configure Redis for rate limiting
4. Set up Sentry monitoring
5. Enable secure headers
6. Configure proper session handling
7. Set up API key management
8. Enable error tracking
9. Configure logging
10. Review security settings regularly

## Usage Examples

### Form Validation
```python
from app.security import FormValidation

class RegistrationForm(FlaskForm):
    username = StringField('Username', validators=[FormValidation.validate_username])
    email = StringField('Email', validators=[FormValidation.validate_email])
    password = PasswordField('Password', validators=[FormValidation.validate_password])
```

### API Rate Limiting
```python
from app.security import api_rate_limit

@app.route('/api/data')
@api_rate_limit()
def get_data():
    return {'data': 'content'}
```

### Error Tracking
```python
from app.error_tracking import track_error

@track_error
def process_data():
    # Your code here
    pass
```

## Security Best Practices
1. Keep dependencies updated
2. Use strong password policies
3. Implement proper input validation
4. Enable rate limiting
5. Use HTTPS everywhere
6. Implement proper session management
7. Monitor and log security events
8. Regular security audits
9. Proper error handling
10. Secure configuration management

"""
Security Tests for AgroMap Uzbekistan

This module contains tests for security features of the AgroMap application.
"""

import pytest
import re
import json
from flask import url_for
from bs4 import BeautifulSoup
from app.security import sanitize_input, validate_url, validate_ip, validate_coordinates
import time
import logging
from app.security import FormValidation
from wtforms import Form, StringField, PasswordField
from wtforms.validators import ValidationError

def test_csrf_protection(client):
    """Test that CSRF protection is working."""
    # Get the login page to get a CSRF token
    response = client.get('/login')
    assert response.status_code == 200
    
    # Extract CSRF token from the form
    soup = BeautifulSoup(response.data, 'html.parser')
    csrf_token = soup.find('input', {'name': 'csrf_token'})
    
    # Verify CSRF token exists
    assert csrf_token is not None
    
    # Try to login without CSRF token
    response = client.post('/login', data={
        'email': 'test@example.com',
        'password': 'password'
    })
    
    # Should fail with 400 Bad Request due to missing CSRF token
    assert response.status_code == 400
    
    # Try to login with CSRF token
    response = client.post('/login', data={
        'email': 'test@example.com',
        'password': 'password',
        'csrf_token': csrf_token['value']
    })
    
    # Should redirect to login page with error message (invalid credentials)
    # but not fail due to CSRF
    assert response.status_code == 302 or response.status_code == 200

def test_rate_limiting(client):
    """Test that rate limiting is working."""
    # Make multiple requests to a rate-limited endpoint
    responses = []
    endpoint = '/api/weather'  # Use a rate-limited API endpoint
    
    # Make 60 requests (should hit hourly limit of 50)
    for _ in range(60):
        responses.append(client.get(endpoint))
        time.sleep(0.1)  # Small delay to prevent overwhelming
    
    # Verify rate limiting kicked in
    assert any(r.status_code == 429 for r in responses), "Rate limiting not working"
    
    # Check rate limit headers exist
    assert 'X-RateLimit-Limit' in responses[0].headers
    assert 'X-RateLimit-Remaining' in responses[0].headers

def test_security_headers(client):
    """Test that security headers are properly set."""
    response = client.get('/')
    headers = response.headers
    
    # Check essential security headers
    assert headers.get('X-Content-Type-Options') == 'nosniff'
    assert headers.get('X-Frame-Options') == 'SAMEORIGIN'
    assert headers.get('X-XSS-Protection') == '1; mode=block'
    assert 'Content-Security-Policy' in headers
    assert headers.get('Strict-Transport-Security') == 'max-age=31536000; includeSubDomains'
    assert headers.get('Referrer-Policy') == 'strict-origin-when-cross-origin'

def test_input_validation(app):
    """Test input validation utilities."""
    from app.utils import (
        sanitize_string, validate_email, validate_url, validate_integer,
        validate_float, validate_date, validate_ip_address, validate_coordinates,
        validate_json, validate_file_extension
    )
    
    # Test sanitize_string
    assert sanitize_string('<script>alert("XSS")</script>') == 'alert("XSS")'
    assert sanitize_string('Normal text') == 'Normal text'
    assert len(sanitize_string('x' * 1000, max_length=100)) == 100
    
    # Test validate_email
    assert validate_email('valid@example.com') is True
    assert validate_email('invalid-email') is False
    assert validate_email('') is False
    assert validate_email(None) is False
    
    # Test validate_url
    assert validate_url('https://example.com') is True
    assert validate_url('ftp://example.com') is False
    assert validate_url('https://example.com', allowed_domains=['example.com']) is True
    assert validate_url('https://malicious.com', allowed_domains=['example.com']) is False
    
    # Test validate_integer
    assert validate_integer(10) is True
    assert validate_integer('10') is True
    assert validate_integer(10, min_value=5, max_value=15) is True
    assert validate_integer(10, min_value=15) is False
    assert validate_integer(10, max_value=5) is False
    assert validate_integer('abc') is False
    
    # Test validate_float
    assert validate_float(10.5) is True
    assert validate_float('10.5') is True
    assert validate_float(10.5, min_value=5.5, max_value=15.5) is True
    assert validate_float(10.5, min_value=15.5) is False
    assert validate_float(10.5, max_value=5.5) is False
    assert validate_float('abc') is False
    
    # Test validate_date
    assert validate_date('2023-01-01') is True
    assert validate_date('01/01/2023', format='%m/%d/%Y') is True
    assert validate_date('invalid-date') is False
    
    # Test validate_ip_address
    assert validate_ip_address('192.168.1.1') is True
    assert validate_ip_address('2001:0db8:85a3:0000:0000:8a2e:0370:7334') is True
    assert validate_ip_address('invalid-ip') is False
    
    # Test validate_coordinates
    assert validate_coordinates(37.7749, -122.4194) is True
    assert validate_coordinates(91, 0) is False  # Latitude out of range
    assert validate_coordinates(0, 181) is False  # Longitude out of range
    assert validate_coordinates('abc', 0) is False
    
    # Test validate_json
    assert validate_json('{"key": "value"}') is True
    assert validate_json('invalid-json') is False
    assert validate_json({'key': 'value'}) is True
    
    # Test validate_file_extension
    assert validate_file_extension('image.jpg', ['.jpg', '.png']) is True
    assert validate_file_extension('image.gif', ['.jpg', '.png']) is False
    assert validate_file_extension('', ['.jpg']) is False

def test_error_tracking(app, client, monkeypatch):
    """Test error tracking configuration."""
    # Mock the Sentry SDK to verify it's initialized
    class MockSentry:
        initialized = False
        
        @classmethod
        def init(cls, **kwargs):
            cls.initialized = True
            cls.kwargs = kwargs
    
    monkeypatch.setattr('sentry_sdk.init', MockSentry.init)
    
    # Re-initialize the app to trigger Sentry initialization
    app.config['TESTING'] = False
    with app.app_context():
        from app import create_app
        create_app()
    
    # Verify Sentry was initialized
    assert MockSentry.initialized
    assert 'integrations' in MockSentry.kwargs
    assert 'environment' in MockSentry.kwargs

def test_backup_system():
    """Test backup system functionality."""
    from app.utils.backup import BackupSystem
    import tempfile
    import os
    
    # Create a temporary directory for testing
    with tempfile.TemporaryDirectory() as temp_dir:
        # Configure backup system with test settings
        config = {
            'backup_dir': temp_dir,
            'use_s3': False,
            'local_retention_days': 1
        }
        
        # Initialize backup system
        backup = BackupSystem(config)
        
        # Test backup directory creation
        assert os.path.exists(temp_dir)
        
        # Test timestamp generation
        assert backup.timestamp is not None
        assert re.match(r'\d{8}_\d{6}', backup.timestamp)
        
        # Test configuration loading
        assert backup.backup_dir == temp_dir
        assert backup.use_s3 is False
        assert backup.local_retention_days == 1

def test_secure_cookies(client):
    """Test that cookies are set with secure attributes."""
    # Create a test user and log them in
    response = client.post('/login', data={
        'email': 'test@example.com',
        'password': 'password',
        'csrf_token': client.get('/login').data.decode('utf-8').split('name="csrf_token" value="')[1].split('"')[0]
    }, follow_redirects=True)
    
    # Get the cookies
    cookies = client.cookie_jar
    
    # Check for session cookie
    for cookie in cookies:
        if cookie.name == 'session':
            # In testing mode, secure might be False, but httpOnly should be True
            assert cookie.has_nonstandard_attr('HttpOnly')
            break
    else:
        pytest.fail("Session cookie not found")

def test_input_sanitization():
    """Test input sanitization functions."""
    # Test string sanitization
    malicious_input = '<script>alert("xss")</script>Hello'
    sanitized = sanitize_input(malicious_input)
    assert '<script>' not in sanitized
    assert 'Hello' in sanitized
    
    # Test dictionary sanitization
    malicious_dict = {
        'name': '<img src=x onerror=alert("xss")>John',
        'age': 25
    }
    sanitized = sanitize_input(malicious_dict)
    assert '<img' not in sanitized['name']
    assert 'John' in sanitized['name']
    assert sanitized['age'] == 25

def test_url_validation():
    """Test URL validation function."""
    assert validate_url('https://example.com')
    assert validate_url('http://sub.example.com/path?query=1')
    assert not validate_url('javascript:alert(1)')
    assert not validate_url('data:text/html,<script>alert(1)</script>')
    assert not validate_url('ftp://example.com')

def test_ip_validation():
    """Test IP address validation."""
    assert validate_ip('192.168.1.1')
    assert validate_ip('2001:0db8:85a3:0000:0000:8a2e:0370:7334')
    assert not validate_ip('256.256.256.256')
    assert not validate_ip('not-an-ip')

def test_coordinate_validation():
    """Test coordinate validation."""
    assert validate_coordinates(41.2995, 69.2401)  # Tashkent coordinates
    assert not validate_coordinates(91.2995, 69.2401)  # Invalid latitude
    assert not validate_coordinates(41.2995, 181.2401)  # Invalid longitude
    assert not validate_coordinates('not-a-lat', 'not-a-lon')

def test_api_key_protection(client):
    """Test API key protection."""
    # Test without API key
    response = client.get('/api/weather')
    assert response.status_code == 401
    
    # Test with invalid API key
    response = client.get('/api/weather', headers={'X-API-Key': 'invalid-key'})
    assert response.status_code == 401
    
    # Test with valid API key (you'll need to add a valid key for testing)
    valid_key = 'test-api-key'  # Replace with a valid test key
    response = client.get('/api/weather', headers={'X-API-Key': valid_key})
    assert response.status_code == 200

def test_session_security(client):
    """Test session security features."""
    # Login to create a session
    login_data = {
        'email': 'test@example.com',
        'password': 'password'
    }
    response = client.post('/login', data=login_data)
    
    # Check session cookie security flags
    session_cookie = next((c for c in client.cookie_jar if c.name == 'session'), None)
    assert session_cookie is not None
    assert session_cookie.secure  # Ensures cookie is only sent over HTTPS
    assert session_cookie.has_nonstandard_attr('HttpOnly')  # Prevents JavaScript access
    
    # Test session expiry
    time.sleep(2)  # Wait briefly
    response = client.get('/profile')  # Access protected route
    assert response.status_code in [200, 302]  # Should still work within expiry

@pytest.mark.parametrize('endpoint', [
    '/api/weather',
    '/api/crop-reports',
    '/api/analytics',
    '/api/predictions'
])
def test_api_endpoint_security(client, endpoint):
    """Test security of API endpoints."""
    # Test CORS headers
    response = client.get(endpoint, headers={'Origin': 'https://malicious-site.com'})
    assert 'Access-Control-Allow-Origin' not in response.headers
    
    # Test method not allowed
    response = client.delete(endpoint)
    assert response.status_code == 405
    
    # Test content type enforcement
    response = client.post(endpoint, data='not-json')
    assert response.status_code in [400, 415]

def test_security_logging(app, caplog):
    """Test security event logging."""
    with app.test_client() as client:
        # Test failed login logging
        with caplog.at_level(logging.INFO):
            client.post('/auth/login', data={
                'username': 'nonexistent',
                'password': 'wrongpass'
            })
            assert 'failed_login' in caplog.text
            
        # Test unauthorized access logging
        with caplog.at_level(logging.INFO):
            client.get('/api/protected')
            assert 'unauthorized_access' in caplog.text

def test_api_rate_limiting(app):
    """Test API rate limiting."""
    with app.test_client() as client:
        # Make multiple requests to trigger rate limit
        for _ in range(101):  # Exceeds the 100/hour limit
            response = client.get('/api/test')
            if response.status_code == 429:  # Too Many Requests
                break
        else:
            pytest.fail("Rate limiting did not trigger")

class TestForm(Form):
    """Test form for validation."""
    username = StringField('Username', validators=[FormValidation.validate_username])
    email = StringField('Email', validators=[FormValidation.validate_email])
    password = PasswordField('Password', validators=[FormValidation.validate_password])

def test_password_validation():
    """Test password validation rules."""
    form = TestForm()
    
    # Test short password
    form.password.data = 'short'
    with pytest.raises(ValidationError, match='at least 8 characters'):
        FormValidation.validate_password(form, form.password)
    
    # Test missing uppercase
    form.password.data = 'lowercase123!'
    with pytest.raises(ValidationError, match='uppercase'):
        FormValidation.validate_password(form, form.password)
    
    # Test missing lowercase
    form.password.data = 'UPPERCASE123!'
    with pytest.raises(ValidationError, match='lowercase'):
        FormValidation.validate_password(form, form.password)
    
    # Test missing number
    form.password.data = 'Password!'
    with pytest.raises(ValidationError, match='number'):
        FormValidation.validate_password(form, form.password)
    
    # Test missing special character
    form.password.data = 'Password123'
    with pytest.raises(ValidationError, match='special character'):
        FormValidation.validate_password(form, form.password)
    
    # Test valid password
    form.password.data = 'Password123!'
    FormValidation.validate_password(form, form.password)  # Should not raise

def test_username_validation():
    """Test username validation rules."""
    form = TestForm()
    
    # Test too short
    form.username.data = 'ab'
    with pytest.raises(ValidationError):
        FormValidation.validate_username(form, form.username)
    
    # Test invalid characters
    form.username.data = 'user@name'
    with pytest.raises(ValidationError):
        FormValidation.validate_username(form, form.username)
    
    # Test valid username
    form.username.data = 'valid_username-123'
    FormValidation.validate_username(form, form.username)  # Should not raise

def test_email_validation():
    """Test email validation rules."""
    form = TestForm()
    
    # Test invalid format
    form.email.data = 'notanemail'
    with pytest.raises(ValidationError):
        FormValidation.validate_email(form, form.email)
    
    # Test missing domain
    form.email.data = 'user@'
    with pytest.raises(ValidationError):
        FormValidation.validate_email(form, form.email)
    
    # Test valid email
    form.email.data = 'user@example.com'
    FormValidation.validate_email(form, form.email)  # Should not raise
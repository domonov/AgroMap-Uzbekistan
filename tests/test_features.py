"""Feature testing module for AgroMap."""
import pytest
from flask import url_for
from app.models import User, Crop, Weather, Prediction
from bs4 import BeautifulSoup

def test_user_authentication(client):
    """Test user authentication features."""
    # Test registration
    response = client.post('/register', data={
        'username': 'testuser',
        'email': 'test@example.com',
        'password': 'Test123!',
        'confirm_password': 'Test123!'
    }, follow_redirects=True)
    assert b'Registration successful' in response.data
    
    # Test login
    response = client.post('/login', data={
        'email': 'test@example.com',
        'password': 'Test123!'
    }, follow_redirects=True)
    assert b'Login successful' in response.data
    
    # Test password reset
    response = client.post('/reset-password', data={
        'email': 'test@example.com'
    }, follow_redirects=True)
    assert b'Password reset instructions sent' in response.data

def test_crop_management(client, auth):
    """Test crop management features."""
    auth.login()  # Login first
    
    # Test adding a crop
    response = client.post('/crops/add', data={
        'name': 'Test Crop',
        'type': 'Grain',
        'planted_date': '2025-05-18',
        'field_size': 100
    }, follow_redirects=True)
    assert b'Crop added successfully' in response.data
    
    # Test viewing crops
    response = client.get('/crops')
    assert b'Test Crop' in response.data
    
    # Test updating a crop
    response = client.post('/crops/1/edit', data={
        'name': 'Updated Crop',
        'type': 'Grain',
        'planted_date': '2025-05-18',
        'field_size': 150
    }, follow_redirects=True)
    assert b'Crop updated successfully' in response.data

def test_weather_features(client, auth):
    """Test weather integration features."""
    auth.login()
    
    # Test current weather
    response = client.get('/weather/current')
    assert response.status_code == 200
    assert b'Current Weather' in response.data
    
    # Test weather forecast
    response = client.get('/weather/forecast')
    assert response.status_code == 200
    assert b'Weather Forecast' in response.data
    
    # Test historical weather
    response = client.get('/weather/historical')
    assert response.status_code == 200
    assert b'Historical Weather' in response.data

def test_map_features(client, auth):
    """Test map functionality."""
    auth.login()
    
    # Test loading map
    response = client.get('/map')
    assert response.status_code == 200
    assert b'Leaflet.js' in response.data
    
    # Test map layers
    response = client.get('/api/map/layers')
    assert response.status_code == 200
    data = response.get_json()
    assert 'layers' in data
    
    # Test drawing tools
    response = client.get('/map')
    assert b'L.Draw' in response.data

def test_analytics_features(client, auth):
    """Test analytics functionality."""
    auth.login()
    
    # Test analytics dashboard
    response = client.get('/analytics')
    assert response.status_code == 200
    assert b'Chart.js' in response.data
    
    # Test data export
    response = client.get('/analytics/export')
    assert response.status_code == 200
    assert response.headers['Content-Type'] == 'application/vnd.ms-excel'

def test_mobile_support(client):
    """Test mobile responsive features."""
    mobile_headers = {
        'User-Agent': 'Mozilla/5.0 (iPhone; CPU iPhone OS 14_0 like Mac OS X)'
    }
    
    # Test responsive layout
    response = client.get('/', headers=mobile_headers)
    assert response.status_code == 200
    assert b'viewport' in response.data
    
    # Test touch features
    response = client.get('/map', headers=mobile_headers)
    assert b'touchstart' in response.data
    assert b'touchmove' in response.data

def test_offline_mode(client):
    """Test offline functionality."""
    # Test service worker registration
    response = client.get('/')
    assert b'serviceWorker' in response.data
    
    # Test offline page
    response = client.get('/offline')
    assert response.status_code == 200
    assert b'Offline Mode' in response.data
    
    # Test cache manifest
    response = client.get('/manifest.json')
    assert response.status_code == 200
    data = response.get_json()
    assert 'offline_enabled' in data

def test_translations(client):
    """Test application translations."""
    # Test Uzbek translation
    response = client.get('/?lang=uz')
    assert response.status_code == 200
    
    # Test Russian translation
    response = client.get('/?lang=ru')
    assert response.status_code == 200
    
    # Test English translation
    response = client.get('/?lang=en')
    assert response.status_code == 200

#!/usr/bin/env python3
"""
Working test suite for AgroMap Uzbekistan application
"""

import pytest
import sys
import os
import json
from datetime import datetime

# Add the app directory to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '.'))

def test_weather_service_basic():
    """Test basic weather service functionality"""
    from app.services.weather_service import WeatherService
    
    # Test without API key (fallback mode)
    weather_service = WeatherService(None)
    
    # Test coordinates for Tashkent
    weather = weather_service.get_weather(41.2995, 69.2401)
    
    assert weather is not None
    assert 'main' in weather
    assert 'temp' in weather['main']
    assert 'humidity' in weather['main']
    assert isinstance(weather['main']['temp'], (int, float))
    print("✅ Weather service basic test passed")


def test_weather_service_forecast():
    """Test weather forecast functionality"""
    from app.services.weather_service import WeatherService
    
    weather_service = WeatherService(None)
    forecast = weather_service.get_forecast(41.2995, 69.2401)
    
    assert forecast is not None
    assert 'list' in forecast
    assert len(forecast['list']) > 0
    print("✅ Weather forecast test passed")


def test_weather_service_agricultural_analysis():
    """Test agricultural alerts functionality"""
    from app.services.weather_service import WeatherService
    
    weather_service = WeatherService(None)
    
    # Test agricultural alerts
    alerts = weather_service.get_agricultural_alerts(41.2995, 69.2401)
    
    assert isinstance(alerts, list)  # Should return a list of alerts
    print("✅ Weather agricultural alerts test passed")


def test_market_analyzer_basic():
    """Test basic market analyzer functionality without database"""
    from app.services.market_analyzer import MarketAnalyzer
    
    analyzer = MarketAnalyzer()
    
    # Test harvest price prediction (doesn't need database)
    harvest_prediction = analyzer.predict_harvest_price('wheat', '2024-03-15', 100.0)
    assert harvest_prediction is not None
    assert 'predicted_price' in harvest_prediction
    assert isinstance(harvest_prediction['predicted_price'], (int, float))
    
    # Test historical prices exist
    assert hasattr(analyzer, 'historical_prices')
    assert 'wheat' in analyzer.historical_prices
    assert len(analyzer.historical_prices['wheat']) > 0
    
    print("✅ Market analyzer basic test passed")


def test_crop_advisor_basic():
    """Test basic crop advisor functionality"""
    from app.services.crop_advisor import CropAdvisor
    
    advisor = CropAdvisor()
      # Test planting time recommendation
    planting_info = advisor.get_planting_time('wheat')
    assert planting_info is not None
    
    # Test rotation suggestions
    rotation = advisor.get_rotation_suggestions('wheat')
    assert isinstance(rotation, list)
    
    # Test planting calendar exists
    assert hasattr(advisor, 'planting_calendar')
    assert len(advisor.planting_calendar) > 0
    
    print("✅ Crop advisor basic test passed")


def test_flask_routes_with_context():
    """Test Flask routes with proper application context"""
    from app import create_app
    
    app = create_app()
    
    with app.app_context():
        client = app.test_client()
        
        # Test home route
        response = client.get('/')
        assert response.status_code == 200
        assert b'AgroMap' in response.data
          # Test weather API route
        response = client.get('/api/weather?lat=41.2995&lon=69.2401')
        assert response.status_code == 200
        
        data = json.loads(response.data)
        # Check for either success wrapper or direct weather data
        assert 'main' in data or ('success' in data and data['success'] is True)
          # Test weather forecast route
        response = client.get('/api/weather/forecast?lat=41.2995&lon=69.2401')
        assert response.status_code == 200
        
        data = json.loads(response.data)
        # Check for either success wrapper or direct forecast data
        assert 'list' in data or ('success' in data and data['success'] is True)
          # Test weather alerts route
        response = client.get('/api/weather/alerts?lat=41.2995&lon=69.2401')
        assert response.status_code == 200
        
        data = json.loads(response.data)
        # Check for alerts data structure
        assert 'alerts' in data or ('success' in data and data['success'] is True)
        
        print("✅ Flask routes test passed")


def test_market_analyzer_with_context():
    """Test market analyzer with proper Flask context"""
    from app import create_app
    from app.services.market_analyzer import MarketAnalyzer
    
    app = create_app()
    
    with app.app_context():
        analyzer = MarketAnalyzer()
        
        # Test market conditions analysis
        analysis = analyzer.analyze_market_conditions('wheat')
        # This might return None if no data, which is expected
        assert analysis is None or isinstance(analysis, dict)
        
        # Test planting recommendations
        recommendations = analyzer.get_planting_recommendations()
        assert recommendations is not None
        
        print("✅ Market analyzer with context test passed")


def test_integration_weather_to_frontend():
    """Test integration from weather service to frontend API"""
    from app import create_app
    
    app = create_app()
    
    with app.app_context():
        client = app.test_client()
        
        # Test complete weather workflow
        response = client.get('/api/weather?lat=41.2995&lon=69.2401')
        assert response.status_code == 200
        
        data = json.loads(response.data)
        
        # Check if agricultural data is present
        assert 'agricultural' in data
        assert 'growing_degree_days' in data['agricultural']
        assert 'heat_stress_risk' in data['agricultural']
        
        print("✅ Weather integration test passed")


if __name__ == '__main__':
    print("🧪 Running AgroMap Test Suite...")
    print("=" * 50)
    
    # Run tests manually since pytest has issues
    test_functions = [
        test_weather_service_basic,
        test_weather_service_forecast,
        test_weather_service_agricultural_analysis,
        test_market_analyzer_basic,
        test_crop_advisor_basic,
        test_flask_routes_with_context,
        test_market_analyzer_with_context,
        test_integration_weather_to_frontend
    ]
    
    passed = 0
    failed = 0
    
    for test_func in test_functions:
        try:
            print(f"\n🔍 Running {test_func.__name__}...")
            test_func()
            passed += 1
        except Exception as e:
            print(f"❌ {test_func.__name__} failed: {e}")
            failed += 1
    
    print("\n" + "=" * 50)
    print(f"📊 Test Results: {passed} passed, {failed} failed")
    
    if failed == 0:
        print("🎉 All tests passed!")
    else:
        print(f"⚠️  {failed} tests failed")
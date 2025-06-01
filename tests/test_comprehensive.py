#!/usr/bin/env python3
"""
Comprehensive test suite for AgroMap Uzbekistan application
"""

import pytest
import sys
import os
import json
from unittest.mock import Mock, patch, MagicMock

# Add the app directory to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '.'))

class TestWeatherService:
    """Test cases for weather service"""
    
    def setup_method(self):
        """Setup for each test method"""
        from app.services.weather_service import WeatherService
        self.weather_service = WeatherService(None)  # No API key for testing
    
    def test_get_weather_fallback(self):
        """Test weather service fallback functionality"""
        # Test coordinates for Tashkent
        lat, lon = 41.2995, 69.2401
        
        weather = self.weather_service.get_weather(lat, lon)
        
        assert weather is not None
        assert 'main' in weather
        assert 'temp' in weather['main']
        assert 'humidity' in weather['main']
        assert isinstance(weather['main']['temp'], (int, float))
        assert isinstance(weather['main']['humidity'], (int, float))
    
    def test_get_forecast_fallback(self):
        """Test weather forecast fallback functionality"""
        lat, lon = 41.2995, 69.2401
        
        forecast = self.weather_service.get_forecast(lat, lon)
        
        assert forecast is not None
        assert 'list' in forecast
        assert len(forecast['list']) > 0
        assert 'main' in forecast['list'][0]
    
    def test_agricultural_analysis(self):
        """Test agricultural conditions analysis"""
        mock_weather = {
            'main': {'temp': 25, 'humidity': 60},
            'weather': [{'main': 'Clear'}],
            'wind': {'speed': 3}
        }
        
        analysis = self.weather_service.analyze_agricultural_conditions(mock_weather)
        
        assert 'soil_moisture' in analysis
        assert 'growing_conditions' in analysis
        assert 'recommendation' in analysis
        assert analysis['growing_conditions'] in ['poor', 'fair', 'good', 'excellent']
    
    def test_crop_recommendations(self):
        """Test crop recommendations based on weather"""
        mock_weather = {
            'main': {'temp': 20, 'humidity': 50},
            'weather': [{'main': 'Clear'}]
        }
        
        recommendations = self.weather_service.get_crop_recommendations(mock_weather)
        
        assert isinstance(recommendations, list)
        assert len(recommendations) > 0
        for rec in recommendations:
            assert 'crop' in rec
            assert 'suitability' in rec
            assert 'reason' in rec


class TestMarketAnalyzer:
    """Test cases for market analyzer"""
    
    def setup_method(self):
        """Setup for each test method"""
        from app.services.market_analyzer import MarketAnalyzer
        self.market_analyzer = MarketAnalyzer()
    
    def test_get_crop_prices(self):
        """Test getting crop prices"""
        prices = self.market_analyzer.get_crop_prices()
        
        assert isinstance(prices, dict)
        assert len(prices) > 0
        
        for crop, price_info in prices.items():
            assert 'current_price' in price_info
            assert 'trend' in price_info
            assert isinstance(price_info['current_price'], (int, float))
    
    def test_predict_price(self):
        """Test price prediction"""
        prediction = self.market_analyzer.predict_price('wheat')
        
        assert isinstance(prediction, dict)
        assert 'predicted_price' in prediction
        assert 'confidence' in prediction
        assert 'factors' in prediction
        assert isinstance(prediction['predicted_price'], (int, float))
        assert 0 <= prediction['confidence'] <= 1
    
    def test_get_market_trends(self):
        """Test market trends analysis"""
        trends = self.market_analyzer.get_market_trends()
        
        assert isinstance(trends, dict)
        assert 'overall_trend' in trends
        assert 'top_gaining' in trends
        assert 'top_losing' in trends


class TestCropAdvisor:
    """Test cases for crop advisor"""
    
    def setup_method(self):
        """Setup for each test method"""
        from app.services.crop_advisor import CropAdvisor
        self.crop_advisor = CropAdvisor()
    
    def test_get_crop_recommendations(self):
        """Test crop recommendations"""
        location = {'lat': 41.2995, 'lon': 69.2401}
        soil_type = 'loamy'
        season = 'spring'
        
        recommendations = self.crop_advisor.get_recommendations(location, soil_type, season)
        
        assert isinstance(recommendations, list)
        assert len(recommendations) > 0
        
        for rec in recommendations:
            assert 'crop' in rec
            assert 'suitability' in rec
            assert 'planting_advice' in rec
    
    def test_analyze_soil_suitability(self):
        """Test soil suitability analysis"""
        soil_data = {
            'type': 'loamy',
            'ph': 6.5,
            'nutrients': {'nitrogen': 'medium', 'phosphorus': 'high', 'potassium': 'medium'}
        }
        
        suitability = self.crop_advisor.analyze_soil_suitability('wheat', soil_data)
        
        assert isinstance(suitability, dict)
        assert 'score' in suitability
        assert 'factors' in suitability
        assert 0 <= suitability['score'] <= 100
    
    def test_get_planting_calendar(self):
        """Test planting calendar"""
        location = {'lat': 41.2995, 'lon': 69.2401}
        
        calendar = self.crop_advisor.get_planting_calendar(location)
        
        assert isinstance(calendar, dict)
        assert len(calendar) > 0
        
        for month, crops in calendar.items():
            assert isinstance(crops, list)


class TestFlaskRoutes:
    """Test cases for Flask routes"""
    
    def setup_method(self):
        """Setup for each test method"""
        from app import create_app
        self.app = create_app()
        self.client = self.app.test_client()
        self.app_context = self.app.app_context()
        self.app_context.push()
    
    def teardown_method(self):
        """Cleanup after each test method"""
        self.app_context.pop()
    
    def test_home_route(self):
        """Test home page route"""
        response = self.client.get('/')
        assert response.status_code == 200
        assert b'AgroMap' in response.data
    
    def test_weather_api_route(self):
        """Test weather API route"""
        response = self.client.get('/api/weather?lat=41.2995&lon=69.2401')
        assert response.status_code == 200
        
        data = json.loads(response.data)
        assert 'success' in data
        assert data['success'] is True
        assert 'data' in data
    
    def test_weather_forecast_route(self):
        """Test weather forecast API route"""
        response = self.client.get('/api/weather/forecast?lat=41.2995&lon=69.2401')
        assert response.status_code == 200
        
        data = json.loads(response.data)
        assert 'success' in data
        assert data['success'] is True
    
    def test_weather_alerts_route(self):
        """Test weather alerts API route"""
        response = self.client.get('/api/weather/alerts?lat=41.2995&lon=69.2401')
        assert response.status_code == 200
        
        data = json.loads(response.data)
        assert 'success' in data
        assert isinstance(data.get('alerts', []), list)
    
    def test_crop_reports_get(self):
        """Test getting crop reports"""
        response = self.client.get('/api/crop-reports')
        assert response.status_code == 200
        
        data = json.loads(response.data)
        assert isinstance(data, list)
    
    def test_market_prices_route(self):
        """Test market prices API route"""
        response = self.client.get('/api/market-prices')
        assert response.status_code == 200
        
        data = json.loads(response.data)
        assert isinstance(data, dict)


class TestDatabaseModels:
    """Test cases for database models"""
    
    def setup_method(self):
        """Setup for each test method"""
        from app import create_app, db
        from app.models import CropReport, MarketPrice, User
        
        self.app = create_app()
        self.app_context = self.app.app_context()
        self.app_context.push()
        
        self.db = db
        self.CropReport = CropReport
        self.MarketPrice = MarketPrice
        self.User = User
    
    def teardown_method(self):
        """Cleanup after each test method"""
        self.app_context.pop()
    
    def test_crop_report_model(self):
        """Test CropReport model"""
        # Create a test crop report
        report = self.CropReport(
            crop_type='wheat',
            latitude=41.2995,
            longitude=69.2401,
            area=100.0,
            planting_date='2024-03-15',
            expected_harvest='2024-07-15'
        )
        
        assert report.crop_type == 'wheat'
        assert report.latitude == 41.2995
        assert report.longitude == 69.2401
        assert report.area == 100.0
    
    def test_market_price_model(self):
        """Test MarketPrice model"""
        # Create a test market price
        price = self.MarketPrice(
            crop_type='wheat',
            price=50000.0,
            unit='ton',
            market_location='Tashkent'
        )
        
        assert price.crop_type == 'wheat'
        assert price.price == 50000.0
        assert price.unit == 'ton'
        assert price.market_location == 'Tashkent'
    
    def test_user_model(self):
        """Test User model"""
        # Create a test user
        user = self.User(
            username='testuser',
            email='test@example.com',
            farmer_type='small_scale'
        )
        
        assert user.username == 'testuser'
        assert user.email == 'test@example.com'
        assert user.farmer_type == 'small_scale'


class TestIntegration:
    """Integration tests"""
    
    def setup_method(self):
        """Setup for integration tests"""
        from app import create_app
        self.app = create_app()
        self.client = self.app.test_client()
        self.app_context = self.app.app_context()
        self.app_context.push()
    
    def teardown_method(self):
        """Cleanup after integration tests"""
        self.app_context.pop()
    
    def test_weather_and_crop_integration(self):
        """Test integration between weather service and crop advisor"""
        # Get weather data
        weather_response = self.client.get('/api/weather?lat=41.2995&lon=69.2401')
        assert weather_response.status_code == 200
        
        weather_data = json.loads(weather_response.data)
        assert weather_data['success'] is True
        
        # Check if agricultural analysis is present
        assert 'agricultural_conditions' in weather_data['data']
        assert 'growing_conditions' in weather_data['data']['agricultural_conditions']
    
    def test_full_workflow(self):
        """Test a complete user workflow"""
        # 1. Get weather data
        weather_response = self.client.get('/api/weather?lat=41.2995&lon=69.2401')
        assert weather_response.status_code == 200
        
        # 2. Get market prices
        market_response = self.client.get('/api/market-prices')
        assert market_response.status_code == 200
        
        # 3. Get crop reports
        reports_response = self.client.get('/api/crop-reports')
        assert reports_response.status_code == 200
        
        # All requests should be successful
        assert all(resp.status_code == 200 for resp in [weather_response, market_response, reports_response])


if __name__ == '__main__':
    # Run tests if script is executed directly
    pytest.main([__file__, '-v'])

#!/usr/bin/env python3
"""
Simple test cases for AgroMap Uzbekistan application
"""

import pytest
import sys
import os
import json

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


def test_weather_service_forecast():
    """Test weather forecast functionality"""
    from app.services.weather_service import WeatherService
    
    weather_service = WeatherService(None)
    forecast = weather_service.get_forecast(41.2995, 69.2401)
    
    assert forecast is not None
    assert 'list' in forecast
    assert len(forecast['list']) > 0


def test_weather_service_agricultural_analysis():
    """Test agricultural analysis"""
    from app.services.weather_service import WeatherService
    
    weather_service = WeatherService(None)
    mock_weather = {
        'main': {'temp': 25, 'humidity': 60},
        'weather': [{'main': 'Clear'}],
        'wind': {'speed': 3}
    }
    
    analysis = weather_service.analyze_agricultural_conditions(mock_weather)
    
    assert 'soil_moisture' in analysis
    assert 'growing_conditions' in analysis
    assert 'recommendation' in analysis


def test_market_analyzer_basic():
    """Test basic market analyzer functionality"""
    from app.services.market_analyzer import MarketAnalyzer
    
    analyzer = MarketAnalyzer()
    
    # Test market conditions analysis
    analysis = analyzer.analyze_market_conditions('wheat')
    assert analysis is not None
    
    # Test harvest price prediction
    harvest_prediction = analyzer.predict_harvest_price('wheat', '2024-03-15', 100.0)
    assert harvest_prediction is not None
    
    # Test planting recommendations
    recommendations = analyzer.get_planting_recommendations()
    assert recommendations is not None


def test_market_analyzer_supply_demand():
    """Test market analysis features"""
    from app.services.market_analyzer import MarketAnalyzer
    
    analyzer = MarketAnalyzer()
    
    # Test historical prices exist
    assert hasattr(analyzer, 'historical_prices')
    assert 'wheat' in analyzer.historical_prices
    
    # Test seasonal factors exist
    assert hasattr(analyzer, 'seasonal_factors')
    assert len(analyzer.seasonal_factors) > 0


def test_crop_advisor_basic():
    """Test basic crop advisor functionality"""
    from app.services.crop_advisor import CropAdvisor
    
    advisor = CropAdvisor()
    location = {'lat': 41.2995, 'lon': 69.2401}
    
    recommendations = advisor.get_recommendations(location, 'loamy', 'spring')
    
    assert isinstance(recommendations, list)
    assert len(recommendations) > 0


if __name__ == '__main__':
    pytest.main([__file__, '-v'])

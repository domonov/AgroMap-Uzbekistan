#!/usr/bin/env python3
"""
Test script for weather service functionality
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '.'))

from app.services.weather_service import WeatherService
import json

def test_weather_service():
    """Test the weather service with and without API key"""
    print("🌤️ Testing Weather Service...")
    print("=" * 50)
    
    # Test without API key (should use fallback)
    print("\n1. Testing without API key (fallback mode):")
    weather_service = WeatherService(None)
    
    # Test coordinates for Tashkent, Uzbekistan
    tashkent_lat, tashkent_lon = 41.2995, 69.2401
    
    print(f"Getting weather for Tashkent ({tashkent_lat}, {tashkent_lon})...")
    weather = weather_service.get_weather(tashkent_lat, tashkent_lon)
    
    if weather:
        print("✅ Weather data received")
        print(f"Temperature: {weather['main']['temp']}°C")
        print(f"Humidity: {weather['main']['humidity']}%")
        print(f"Fallback mode: {weather.get('fallback', False)}")
        
        # Test agricultural data
        if 'agricultural' in weather:
            agri = weather['agricultural']
            print(f"Growing Degree Days: {agri.get('growing_degree_days', 'N/A')}")
            print(f"Heat Stress Risk: {agri.get('heat_stress_risk', 'N/A')}")
            print(f"Irrigation Need: {agri.get('irrigation_need', 'N/A')}")
        
        # Test crop recommendations
        if 'crop_recommendations' in weather:
            print("Crop Recommendations:")
            for crop, status in weather['crop_recommendations'].items():
                print(f"  {crop}: {status}")
    else:
        print("❌ Failed to get weather data")
    
    print("\n2. Testing forecast (3 days):")
    forecast = weather_service.get_forecast(tashkent_lat, tashkent_lon, 3)
    
    if forecast:
        print("✅ Forecast data received")
        print(f"Forecast entries: {len(forecast.get('list', []))}")
        print(f"Fallback mode: {forecast.get('fallback', False)}")
        
        if 'agricultural_summary' in forecast:
            summary = forecast['agricultural_summary']
            print(f"Average temperature: {summary.get('avg_temp', 'N/A')}°C")
            print(f"Total rainfall: {summary.get('total_rainfall', 'N/A')}mm")
            print(f"Optimal days: {summary.get('optimal_days', 'N/A')}")
        
        if 'planting_advice' in forecast:
            print("Planting Advice:")
            for advice in forecast['planting_advice']:
                print(f"  {advice}")
    else:
        print("❌ Failed to get forecast data")
    
    print("\n3. Testing agricultural alerts:")
    alerts = weather_service.get_agricultural_alerts(tashkent_lat, tashkent_lon)
    
    if alerts:
        print(f"✅ Alerts received: {len(alerts)} alerts")
        for alert in alerts:
            print(f"  {alert['icon']} [{alert['severity']}] {alert['message']}")
    else:
        print("✅ No alerts (normal conditions)")
    
    print("\n4. Testing with different locations:")
    test_locations = [
        ("Samarkand", 39.6542, 66.9597),
        ("Bukhara", 39.7747, 64.4286),
        ("Fergana", 40.3833, 71.7833)
    ]
    
    for city, lat, lon in test_locations:
        print(f"\n{city} ({lat}, {lon}):")
        weather = weather_service.get_weather(lat, lon)
        if weather:
            temp = weather['main']['temp']
            print(f"  Temperature: {temp}°C")
            if 'agricultural' in weather:
                heat_risk = weather['agricultural'].get('heat_stress_risk', 'unknown')
                print(f"  Heat stress risk: {heat_risk}")
        else:
            print("  ❌ Failed to get data")
    
    print("\n🎉 Weather service testing completed!")

if __name__ == "__main__":
    test_weather_service()

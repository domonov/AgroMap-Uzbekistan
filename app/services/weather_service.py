import requests
from datetime import datetime, timedelta
import statistics
from typing import Dict, List, Optional

class WeatherService:
    def __init__(self, api_key):
        self.api_key = api_key
        self.base_url = "http://api.openweathermap.org/data/2.5"
        # Fallback data for when API is not available
        self.fallback_enabled = True

    def get_weather(self, lat, lon):
        """Get current weather for location"""
        try:
            if not self.api_key:
                return self._get_fallback_weather(lat, lon)
                
            url = f"{self.base_url}/weather"
            params = {
                'lat': lat,
                'lon': lon,
                'appid': self.api_key,
                'units': 'metric'
            }
            response = requests.get(url, params=params, timeout=10)
            response.raise_for_status()
            data = response.json()
            return self._enhance_weather_data(data)
        except Exception as e:
            print(f"Weather API error: {e}")
            return self._get_fallback_weather(lat, lon) if self.fallback_enabled else None

    def get_forecast(self, lat, lon, days=7):
        """Get weather forecast for location"""
        try:
            if not self.api_key:
                return self._get_fallback_forecast(lat, lon, days)
                
            url = f"{self.base_url}/forecast"
            params = {
                'lat': lat,
                'lon': lon,
                'appid': self.api_key,
                'units': 'metric',
                'cnt': min(days * 8, 40)  # API limit is 40, 8 measurements per day
            }
            response = requests.get(url, params=params, timeout=10)
            response.raise_for_status()
            data = response.json()
            return self._enhance_forecast_data(data)
        except Exception as e:
            print(f"Forecast API error: {e}")
            return self._get_fallback_forecast(lat, lon, days) if self.fallback_enabled else None

    def _enhance_weather_data(self, data):
        """Enhance weather data with agricultural metrics"""
        enhanced = data.copy()
        
        # Add agricultural indicators
        temp = data['main']['temp']
        humidity = data['main']['humidity']
        
        enhanced['agricultural'] = {
            'growing_degree_days': max(0, temp - 10),  # Base temperature for most crops
            'heat_stress_risk': 'high' if temp > 35 else 'medium' if temp > 30 else 'low',
            'irrigation_need': 'high' if humidity < 40 else 'medium' if humidity < 60 else 'low',
            'frost_risk': 'high' if temp < 2 else 'medium' if temp < 5 else 'none',
            'pest_pressure': 'high' if 20 < temp < 30 and humidity > 70 else 'medium',
        }
        
        # Add crop-specific recommendations
        enhanced['crop_recommendations'] = self._get_crop_recommendations(temp, humidity, data.get('wind', {}).get('speed', 0))
        
        return enhanced

    def _enhance_forecast_data(self, data):
        """Enhance forecast data with agricultural analysis"""
        enhanced = data.copy()
        forecast_list = data.get('list', [])
        
        if not forecast_list:
            return enhanced
        
        # Calculate agricultural metrics for the forecast period
        temps = [item['main']['temp'] for item in forecast_list]
        humidity_values = [item['main']['humidity'] for item in forecast_list]
        rain_forecast = [item.get('rain', {}).get('3h', 0) for item in forecast_list]
        
        enhanced['agricultural_summary'] = {
            'avg_temp': round(statistics.mean(temps), 1),
            'min_temp': min(temps),
            'max_temp': max(temps),
            'avg_humidity': round(statistics.mean(humidity_values), 1),
            'total_rainfall': sum(rain_forecast),
            'growing_degree_days': sum(max(0, temp - 10) for temp in temps),
            'frost_days': sum(1 for temp in temps if temp < 2),
            'optimal_days': sum(1 for temp in temps if 18 <= temp <= 28),
        }
        
        # Weekly planting recommendations
        enhanced['planting_advice'] = self._get_planting_advice(enhanced['agricultural_summary'])
        
        return enhanced

    def _get_crop_recommendations(self, temp, humidity, wind_speed):
        """Get crop-specific recommendations based on current weather"""
        recommendations = {}
        
        # Wheat recommendations
        if 15 <= temp <= 25 and humidity > 50:
            recommendations['wheat'] = 'excellent_conditions'
        elif temp > 30:
            recommendations['wheat'] = 'heat_stress_risk'
        else:
            recommendations['wheat'] = 'monitor_conditions'
        
        # Cotton recommendations
        if 20 <= temp <= 35 and humidity < 80:
            recommendations['cotton'] = 'favorable_conditions'
        elif temp < 15:
            recommendations['cotton'] = 'too_cold'
        else:
            recommendations['cotton'] = 'monitor_humidity'
        
        # Rice recommendations
        if 20 <= temp <= 30 and humidity > 60:
            recommendations['rice'] = 'ideal_conditions'
        elif temp > 35:
            recommendations['rice'] = 'heat_stress'
        else:
            recommendations['rice'] = 'acceptable_conditions'
        
        # Vegetables (tomatoes, peppers)
        if 18 <= temp <= 28 and 50 <= humidity <= 70:
            recommendations['vegetables'] = 'optimal_growth'
        elif temp > 32:
            recommendations['vegetables'] = 'heat_protection_needed'
        else:
            recommendations['vegetables'] = 'monitor_temperature'
        
        return recommendations

    def _get_planting_advice(self, summary):
        """Generate planting advice based on forecast summary"""
        advice = []
        
        if summary['frost_days'] > 0:
            advice.append("⚠️ Frost risk detected. Delay planting of frost-sensitive crops.")
        
        if summary['avg_temp'] < 10:
            advice.append("🌡️ Temperatures too low for most crops. Wait for warmer weather.")
        elif summary['avg_temp'] > 35:
            advice.append("🔥 High temperatures expected. Consider heat-resistant varieties.")
        
        if summary['total_rainfall'] < 5:
            advice.append("💧 Low rainfall expected. Ensure irrigation is available.")
        elif summary['total_rainfall'] > 50:
            advice.append("🌧️ Heavy rainfall expected. Ensure good drainage.")
        
        if summary['optimal_days'] >= 5:
            advice.append("✅ Good planting window with optimal temperatures.")
        
        if not advice:
            advice.append("📊 Weather conditions are within normal ranges for planting.")
        
        return advice

    def _get_fallback_weather(self, lat, lon):
        """Provide realistic fallback weather data for Uzbekistan"""
        # Simulate realistic weather for Uzbekistan based on season
        now = datetime.now()
        month = now.month
        
        # Seasonal temperature ranges for Uzbekistan
        if month in [12, 1, 2]:  # Winter
            temp = 5 + (lat - 40) * 2  # Adjust by latitude
            humidity = 70
        elif month in [3, 4, 5]:  # Spring
            temp = 18 + (lat - 40) * 1.5
            humidity = 55
        elif month in [6, 7, 8]:  # Summer
            temp = 32 + (lat - 40) * 1
            humidity = 35
        else:  # Autumn
            temp = 15 + (lat - 40) * 1.5
            humidity = 60
        
        fallback_data = {
            "coord": {"lon": lon, "lat": lat},
            "weather": [{"main": "Clear", "description": "clear sky", "icon": "01d"}],
            "main": {
                "temp": temp,
                "feels_like": temp + 2,
                "temp_min": temp - 3,
                "temp_max": temp + 5,
                "pressure": 1013,
                "humidity": humidity
            },
            "wind": {"speed": 3.5, "deg": 180},
            "dt": int(datetime.now().timestamp()),
            "name": "Local Area",
            "fallback": True
        }
        
        return self._enhance_weather_data(fallback_data)

    def _get_fallback_forecast(self, lat, lon, days):
        """Provide realistic fallback forecast data"""
        forecast_list = []
        base_time = datetime.now()
        
        for i in range(days * 8):  # 8 entries per day (3-hour intervals)
            forecast_time = base_time + timedelta(hours=i * 3)
            month = forecast_time.month
            
            # Seasonal adjustment
            if month in [12, 1, 2]:
                base_temp = 5 + (lat - 40) * 2
                humidity = 70
            elif month in [3, 4, 5]:
                base_temp = 18 + (lat - 40) * 1.5
                humidity = 55
            elif month in [6, 7, 8]:
                base_temp = 32 + (lat - 40) * 1
                humidity = 35
            else:
                base_temp = 15 + (lat - 40) * 1.5
                humidity = 60
            
            # Daily temperature variation
            hour = forecast_time.hour
            temp_variation = 0
            if 6 <= hour <= 18:  # Daytime
                temp_variation = 5 * (1 - abs(hour - 12) / 6)
            else:  # Nighttime
                temp_variation = -3
            
            temp = base_temp + temp_variation
            
            forecast_entry = {
                "dt": int(forecast_time.timestamp()),
                "main": {
                    "temp": temp,
                    "temp_min": temp - 2,
                    "temp_max": temp + 2,
                    "pressure": 1013,
                    "humidity": humidity
                },
                "weather": [{"main": "Clear", "description": "clear sky"}],
                "wind": {"speed": 3.0}
            }
            forecast_list.append(forecast_entry)
        
        fallback_forecast = {
            "list": forecast_list,
            "city": {"name": "Local Area", "coord": {"lat": lat, "lon": lon}},
            "fallback": True
        }
        
        return self._enhance_forecast_data(fallback_forecast)

    def get_agricultural_alerts(self, lat, lon):
        """Get weather-based agricultural alerts"""
        weather = self.get_weather(lat, lon)
        if not weather:
            return []
        
        alerts = []
        temp = weather['main']['temp']
        humidity = weather['main']['humidity']
        
        # Temperature alerts
        if temp > 40:
            alerts.append({
                'type': 'extreme_heat',
                'severity': 'high',
                'message': 'Extreme heat warning. Protect crops and increase irrigation.',
                'icon': '🔥'
            })
        elif temp > 35:
            alerts.append({
                'type': 'heat_stress',
                'severity': 'medium',
                'message': 'High temperatures may stress crops. Monitor soil moisture.',
                'icon': '🌡️'
            })
        
        if temp < 0:
            alerts.append({
                'type': 'hard_freeze',
                'severity': 'high',
                'message': 'Hard freeze warning. Protect sensitive crops.',
                'icon': '❄️'
            })
        elif temp < 5:
            alerts.append({
                'type': 'frost_risk',
                'severity': 'medium',
                'message': 'Frost risk. Consider crop protection measures.',
                'icon': '🧊'
            })
        
        # Humidity alerts
        if humidity < 30:
            alerts.append({
                'type': 'low_humidity',
                'severity': 'medium',
                'message': 'Very low humidity. Increase irrigation and monitor plant stress.',
                'icon': '💧'
            })
        elif humidity > 90:
            alerts.append({
                'type': 'high_humidity',
                'severity': 'medium',
                'message': 'High humidity may increase disease risk. Ensure good ventilation.',
                'icon': '💨'
            })
        
        return alerts
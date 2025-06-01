#!/usr/bin/env python3
"""
Unit tests for AgroMap Uzbekistan application
"""

import unittest
import json
import os
import sys
from unittest.mock import patch, MagicMock

# Add the parent directory to the path to import app modules
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import create_app, db
from app.models import User, CropReport, WeatherData, MapSuggestion
from app.services.weather_service import WeatherService
from app.services.market_analyzer import MarketAnalyzer
from app.services.crop_advisor import CropAdvisor

class WeatherServiceTestCase(unittest.TestCase):
    """Test cases for Weather Service"""
    
    def setUp(self):
        self.weather_service = WeatherService(None)  # Test without API key
        self.test_lat = 41.2995  # Tashkent
        self.test_lon = 69.2401
    
    def test_fallback_weather_data(self):
        """Test that fallback weather data is generated correctly"""
        weather = self.weather_service.get_weather(self.test_lat, self.test_lon)
        
        self.assertIsNotNone(weather)
        self.assertTrue(weather.get('fallback', False))
        self.assertIn('main', weather)
        self.assertIn('temp', weather['main'])
        self.assertIn('humidity', weather['main'])
        self.assertIn('agricultural', weather)
        self.assertIn('crop_recommendations', weather)
    
    def test_agricultural_metrics(self):
        """Test agricultural metrics calculation"""
        weather = self.weather_service.get_weather(self.test_lat, self.test_lon)
        agricultural = weather['agricultural']
        
        self.assertIn('growing_degree_days', agricultural)
        self.assertIn('heat_stress_risk', agricultural)
        self.assertIn('irrigation_need', agricultural)
        self.assertIn('frost_risk', agricultural)
        
        # Test that metrics are reasonable
        self.assertIsInstance(agricultural['growing_degree_days'], (int, float))
        self.assertIn(agricultural['heat_stress_risk'], ['low', 'medium', 'high'])
        self.assertIn(agricultural['irrigation_need'], ['low', 'medium', 'high'])
    
    def test_forecast_data(self):
        """Test forecast data generation"""
        forecast = self.weather_service.get_forecast(self.test_lat, self.test_lon, 3)
        
        self.assertIsNotNone(forecast)
        self.assertIn('list', forecast)
        self.assertIn('agricultural_summary', forecast)
        self.assertIn('planting_advice', forecast)
        
        # Test agricultural summary
        summary = forecast['agricultural_summary']
        self.assertIn('avg_temp', summary)
        self.assertIn('total_rainfall', summary)
        self.assertIn('growing_degree_days', summary)
    
    def test_agricultural_alerts(self):
        """Test agricultural alerts generation"""
        alerts = self.weather_service.get_agricultural_alerts(self.test_lat, self.test_lon)
        
        self.assertIsInstance(alerts, list)
        # Alerts may be empty for normal conditions
        for alert in alerts:
            self.assertIn('type', alert)
            self.assertIn('severity', alert)
            self.assertIn('message', alert)
            self.assertIn('icon', alert)

class MarketAnalyzerTestCase(unittest.TestCase):
    """Test cases for Market Analyzer"""
    
    def setUp(self):
        self.analyzer = MarketAnalyzer()
    
    def test_price_prediction(self):
        """Test price prediction functionality"""
        prediction = self.analyzer.predict_price('wheat', 'tashkent')
        
        self.assertIsNotNone(prediction)
        self.assertIn('current_price', prediction)
        self.assertIn('predicted_price', prediction)
        self.assertIn('change_percent', prediction)
        self.assertIn('confidence', prediction)
        
        # Test that prices are positive
        self.assertGreater(prediction['current_price'], 0)
        self.assertGreater(prediction['predicted_price'], 0)
    
    def test_supply_demand_analysis(self):
        """Test supply and demand analysis"""
        analysis = self.analyzer.analyze_supply_demand('cotton', 'samarkand')
        
        self.assertIsNotNone(analysis)
        self.assertIn('supply_level', analysis)
        self.assertIn('demand_level', analysis)
        self.assertIn('market_balance', analysis)
        
        # Test that levels are valid
        self.assertIn(analysis['supply_level'], ['low', 'medium', 'high'])
        self.assertIn(analysis['demand_level'], ['low', 'medium', 'high'])
    
    def test_market_opportunities(self):
        """Test market opportunities identification"""
        opportunities = self.analyzer.identify_opportunities('fergana')
        
        self.assertIsInstance(opportunities, list)
        self.assertLessEqual(len(opportunities), 5)  # Should return top 5
        
        for opportunity in opportunities:
            self.assertIn('crop', opportunity)
            self.assertIn('score', opportunity)
            self.assertIn('reason', opportunity)
            self.assertIsInstance(opportunity['score'], (int, float))
            self.assertGreaterEqual(opportunity['score'], 0)
            self.assertLessEqual(opportunity['score'], 100)

class FlaskAppTestCase(unittest.TestCase):
    """Test cases for Flask application"""
    
    def setUp(self):
        self.app = create_app()
        self.app.config['TESTING'] = True
        self.app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
        self.client = self.app.test_client()
        
        with self.app.app_context():
            db.create_all()
    
    def tearDown(self):
        with self.app.app_context():
            db.session.remove()
            db.drop_all()
    
    def test_home_page(self):
        """Test that home page loads correctly"""
        response = self.client.get('/')
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'AgroMap', response.data)
    
    def test_weather_api(self):
        """Test weather API endpoint"""
        response = self.client.get('/api/weather?lat=41.2995&lon=69.2401')
        self.assertEqual(response.status_code, 200)
        
        data = json.loads(response.data)
        self.assertIn('main', data)
        self.assertIn('agricultural', data)
        self.assertIn('crop_recommendations', data)
    
    def test_weather_api_missing_params(self):
        """Test weather API with missing parameters"""
        response = self.client.get('/api/weather')
        self.assertEqual(response.status_code, 400)
        
        data = json.loads(response.data)
        self.assertIn('error', data)
    
    def test_forecast_api(self):
        """Test forecast API endpoint"""
        response = self.client.get('/api/weather/forecast?lat=41.2995&lon=69.2401&days=3')
        self.assertEqual(response.status_code, 200)
        
        data = json.loads(response.data)
        self.assertIn('list', data)
        self.assertIn('agricultural_summary', data)
    
    def test_alerts_api(self):
        """Test alerts API endpoint"""
        response = self.client.get('/api/weather/alerts?lat=41.2995&lon=69.2401')
        self.assertEqual(response.status_code, 200)
        
        data = json.loads(response.data)
        self.assertIn('alerts', data)
        self.assertIsInstance(data['alerts'], list)
    
    def test_crop_reports_api(self):
        """Test crop reports API endpoint"""
        # Test GET request
        response = self.client.get('/api/crop-reports')
        self.assertEqual(response.status_code, 200)
        
        data = json.loads(response.data)
        self.assertIsInstance(data, list)
    
    def test_market_analysis_api(self):
        """Test market analysis API endpoint"""
        response = self.client.get('/api/market-analysis?region=tashkent')
        self.assertEqual(response.status_code, 200)
        
        data = json.loads(response.data)
        self.assertIn('opportunities', data)
        self.assertIn('price_trends', data)
    
    def test_price_prediction_api(self):
        """Test price prediction API endpoint"""
        response = self.client.get('/api/price-prediction?crop=wheat&region=tashkent')
        self.assertEqual(response.status_code, 200)
        
        data = json.loads(response.data)
        self.assertIn('current_price', data)
        self.assertIn('predicted_price', data)

class DatabaseModelTestCase(unittest.TestCase):
    """Test cases for database models"""
    
    def setUp(self):
        self.app = create_app()
        self.app.config['TESTING'] = True
        self.app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
        
        with self.app.app_context():
            db.create_all()
            self.app_context = self.app.app_context()
            self.app_context.push()
    
    def tearDown(self):
        db.session.remove()
        db.drop_all()
        self.app_context.pop()
    
    def test_user_model(self):
        """Test User model"""
        user = User(username='testuser', email='test@example.com')
        user.set_password('testpassword')
        db.session.add(user)
        db.session.commit()
        
        # Test password hashing
        self.assertTrue(user.check_password('testpassword'))
        self.assertFalse(user.check_password('wrongpassword'))
        
        # Test string representation
        self.assertEqual(str(user), '<User testuser>')
    
    def test_crop_report_model(self):
        """Test CropReport model"""
        # Create a user first
        user = User(username='farmer1', email='farmer@example.com')
        db.session.add(user)
        db.session.flush()
        
        # Create crop report
        report = CropReport(
            user_id=user.id,
            crop_type='wheat',
            location='Tashkent',
            area=10.5,
            planting_date='2025-03-15',
            expected_harvest='2025-07-15',
            latitude=41.2995,
            longitude=69.2401
        )
        db.session.add(report)
        db.session.commit()
        
        # Test the report was saved correctly
        saved_report = CropReport.query.first()
        self.assertEqual(saved_report.crop_type, 'wheat')
        self.assertEqual(saved_report.location, 'Tashkent')
        self.assertEqual(saved_report.area, 10.5)
    
    def test_weather_data_model(self):
        """Test WeatherData model"""
        weather = WeatherData(
            latitude=41.2995,
            longitude=69.2401,
            temperature=25.5,
            humidity=60,
            wind_speed=5.2,
            precipitation=0.0,
            location='Tashkent'
        )
        db.session.add(weather)
        db.session.commit()
        
        # Test the weather data was saved correctly
        saved_weather = WeatherData.query.first()
        self.assertEqual(saved_weather.temperature, 25.5)
        self.assertEqual(saved_weather.location, 'Tashkent')
    
    def test_map_suggestion_model(self):
        """Test MapSuggestion model"""
        # Create a user first
        user = User(username='contributor', email='contrib@example.com')
        db.session.add(user)
        db.session.flush()
        
        suggestion = MapSuggestion(
            user_id=user.id,
            suggestion_type='crop_boundary',
            location='Samarkand',
            description='Update wheat field boundary',
            latitude=39.6542,
            longitude=66.9597
        )
        db.session.add(suggestion)
        db.session.commit()
        
        # Test the suggestion was saved correctly
        saved_suggestion = MapSuggestion.query.first()
        self.assertEqual(saved_suggestion.suggestion_type, 'crop_boundary')
        self.assertEqual(saved_suggestion.description, 'Update wheat field boundary')

class CropAdvisorTestCase(unittest.TestCase):
    """Test cases for Crop Advisor"""
    
    def setUp(self):
        self.advisor = CropAdvisor()
    
    def test_planting_recommendations(self):
        """Test planting recommendations"""
        recommendations = self.advisor.get_planting_recommendations('tashkent', 'wheat')
        
        self.assertIsNotNone(recommendations)
        self.assertIn('recommended_date', recommendations)
        self.assertIn('soil_preparation', recommendations)
        self.assertIn('variety_suggestions', recommendations)
    
    def test_regional_crops(self):
        """Test regional crop suitability"""
        crops = self.advisor.get_suitable_crops_for_region('fergana')
        
        self.assertIsInstance(crops, list)
        self.assertGreater(len(crops), 0)
        
        for crop in crops:
            self.assertIn('name', crop)
            self.assertIn('suitability_score', crop)
            self.assertIn('reasons', crop)

if __name__ == '__main__':
    # Create test suite
    test_suite = unittest.TestSuite()
    
    # Add test cases
    test_suite.addTest(unittest.makeSuite(WeatherServiceTestCase))
    test_suite.addTest(unittest.makeSuite(MarketAnalyzerTestCase))
    test_suite.addTest(unittest.makeSuite(FlaskAppTestCase))
    test_suite.addTest(unittest.makeSuite(DatabaseModelTestCase))
    test_suite.addTest(unittest.makeSuite(CropAdvisorTestCase))
    
    # Run tests
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(test_suite)
    
    # Print summary
    print("\n" + "="*50)
    print(f"Tests run: {result.testsRun}")
    print(f"Failures: {len(result.failures)}")
    print(f"Errors: {len(result.errors)}")
    
    if result.failures:
        print("\nFailures:")
        for test, traceback in result.failures:
            print(f"- {test}: {traceback}")
    
    if result.errors:
        print("\nErrors:")
        for test, traceback in result.errors:
            print(f"- {test}: {traceback}")
    
    if result.wasSuccessful():
        print("\n🎉 All tests passed!")
    else:
        print("\n❌ Some tests failed.")

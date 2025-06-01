#!/usr/bin/env python3
"""
Simple test runner for AgroMap Uzbekistan application
"""

import os
import sys

# Add the parent directory to the path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

def test_weather_service():
    """Test weather service functionality"""
    print("🌤️ Testing Weather Service...")
    try:
        from app.services.weather_service import WeatherService
        
        # Test fallback mode
        ws = WeatherService(None)
        weather = ws.get_weather(41.2995, 69.2401)
        
        assert weather is not None, "Weather data should not be None"
        assert 'main' in weather, "Weather should have main data"
        assert 'agricultural' in weather, "Weather should have agricultural data"
        assert weather.get('fallback') == True, "Should be in fallback mode"
        
        print("✅ Weather service test passed")
        return True
    except Exception as e:
        print(f"❌ Weather service test failed: {e}")
        return False

def test_market_analyzer():
    """Test market analyzer functionality"""
    print("📊 Testing Market Analyzer...")
    try:
        from app.services.market_analyzer import MarketAnalyzer
        
        analyzer = MarketAnalyzer()
        prediction = analyzer.predict_price('wheat', 'tashkent')
        
        assert prediction is not None, "Price prediction should not be None"
        assert 'current_price' in prediction, "Should have current price"
        assert 'predicted_price' in prediction, "Should have predicted price"
        assert prediction['current_price'] > 0, "Price should be positive"
        
        print("✅ Market analyzer test passed")
        return True
    except Exception as e:
        print(f"❌ Market analyzer test failed: {e}")
        return False

def test_flask_routes():
    """Test Flask application routes"""
    print("🌐 Testing Flask Routes...")
    try:
        from app import create_app
        
        app = create_app()
        app.config['TESTING'] = True
        
        with app.test_client() as client:
            # Test home page
            response = client.get('/')
            assert response.status_code == 200, "Home page should return 200"
            
            # Test weather API
            response = client.get('/api/weather?lat=41.2995&lon=69.2401')
            assert response.status_code == 200, "Weather API should return 200"
            
            # Test invalid weather API request
            response = client.get('/api/weather')
            assert response.status_code == 400, "Invalid weather request should return 400"
        
        print("✅ Flask routes test passed")
        return True
    except Exception as e:
        print(f"❌ Flask routes test failed: {e}")
        return False

def test_database_models():
    """Test database models"""
    print("🗄️ Testing Database Models...")
    try:
        from app import create_app, db
        from app.models import User, CropReport
        
        app = create_app()
        app.config['TESTING'] = True
        app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
        
        with app.app_context():
            db.create_all()
            
            # Test User model
            user = User(username='testuser', email='test@example.com')
            user.set_password('testpass')
            db.session.add(user)
            db.session.commit()
            
            assert user.check_password('testpass'), "Password check should work"
            assert not user.check_password('wrong'), "Wrong password should fail"
            
            # Test CropReport model
            report = CropReport(
                user_id=user.id,
                crop_type='wheat',
                location='Tashkent',
                area=10.0,
                latitude=41.2995,
                longitude=69.2401
            )
            db.session.add(report)
            db.session.commit()
            
            saved_report = CropReport.query.first()
            assert saved_report.crop_type == 'wheat', "Crop type should be saved correctly"
        
        print("✅ Database models test passed")
        return True
    except Exception as e:
        print(f"❌ Database models test failed: {e}")
        return False

def test_crop_advisor():
    """Test crop advisor service"""
    print("🌾 Testing Crop Advisor...")
    try:
        from app.services.crop_advisor import CropAdvisor
        
        advisor = CropAdvisor()
        recommendations = advisor.get_planting_recommendations('tashkent', 'wheat')
        
        assert recommendations is not None, "Recommendations should not be None"
        assert 'recommended_date' in recommendations, "Should have recommended date"
        
        crops = advisor.get_suitable_crops_for_region('fergana')
        assert isinstance(crops, list), "Should return a list of crops"
        assert len(crops) > 0, "Should have at least one suitable crop"
        
        print("✅ Crop advisor test passed")
        return True
    except Exception as e:
        print(f"❌ Crop advisor test failed: {e}")
        return False

def run_all_tests():
    """Run all tests and report results"""
    print("🧪 Running AgroMap Test Suite")
    print("=" * 50)
    
    tests = [
        test_weather_service,
        test_market_analyzer,
        test_flask_routes,
        test_database_models,
        test_crop_advisor
    ]
    
    passed = 0
    total = len(tests)
    
    for test in tests:
        if test():
            passed += 1
        print()
    
    print("=" * 50)
    print(f"Test Results: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 All tests passed! Application is working correctly.")
    else:
        print(f"❌ {total - passed} test(s) failed. Check the output above.")
    
    return passed == total

if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)

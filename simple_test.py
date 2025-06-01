#!/usr/bin/env python3
"""
Simple test to validate enhanced crop services
"""

print("🌾 Testing AgroMap Enhanced Services")
print("=" * 40)

try:
    # Test basic imports
    from datetime import datetime
    import math
    print("✅ Basic imports successful")
    
    # Test crop advisor class definition
    from app.services.crop_advisor import CropAdvisor
    print("✅ CropAdvisor import successful")
    
    # Test yield predictor
    from app.services.yield_predictor import YieldPredictor
    print("✅ YieldPredictor import successful")
    
    # Initialize services
    advisor = CropAdvisor()
    predictor = YieldPredictor()
    print("✅ Services initialized successfully")
    
    # Test basic functionality
    crops = list(advisor.planting_calendar.keys())
    print(f"✅ Available crops: {', '.join(crops)}")
    
    # Test planting time
    wheat_timing = advisor.get_planting_time('wheat')
    print(f"✅ Wheat planting timing: {wheat_timing}")
    
    # Test yield prediction
    yield_result = predictor.predict_yield('wheat', {
        'latitude': 41.2995,
        'longitude': 69.2401
    })
    print(f"✅ Wheat yield prediction: {yield_result['predicted_yield']:.2f} tons/hectare")
    
    # Test smart recommendations
    recommendations = advisor.get_smart_recommendations({
        'latitude': 41.2995,
        'longitude': 69.2401,
        'region': 'Tashkent'
    })
    print(f"✅ Smart recommendations: {len(recommendations)} crops ranked")
    
    print("\n🎉 All enhanced services are working correctly!")
    
except ImportError as e:
    print(f"❌ Import error: {e}")
except Exception as e:
    print(f"❌ Error: {e}")
    import traceback
    traceback.print_exc()

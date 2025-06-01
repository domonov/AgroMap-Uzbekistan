#!/usr/bin/env python3
"""
Test script for the enhanced crop advisor service
"""

import sys
import os

# Add the app directory to Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'app'))

from services.crop_advisor import CropAdvisor

def test_crop_advisor():
    """Test the crop advisor functionality"""
    print("🌾 Testing Enhanced Crop Advisor Service")
    print("=" * 50)
    
    # Initialize crop advisor
    advisor = CropAdvisor()
    
    # Test basic functionality
    print("\n1. Testing Basic Crop List:")
    crops = list(advisor.planting_calendar.keys())
    print(f"Available crops: {', '.join(crops)}")
    
    # Test planting times
    print("\n2. Testing Planting Times:")
    for crop in crops:
        timing = advisor.get_planting_time(crop)
        print(f"{crop.capitalize()}: Start month {timing['start_month']}, End month {timing['end_month']}")
        print(f"  - Optimal now: {timing['is_optimal_now']}")
    
    # Test smart recommendations
    print("\n3. Testing Smart Recommendations:")
    
    # Sample location data (Tashkent coordinates)
    location_data = {
        'latitude': 41.2995,
        'longitude': 69.2401,
        'region': 'Tashkent'
    }
    
    # Sample weather data
    weather_data = {
        'temperature': 25,  # Celsius
        'rainfall': 50,     # mm
        'humidity': 60      # percentage
    }
    
    # Sample soil data
    soil_data = {
        'ph': 7.0,
        'organic_matter': 2.5,  # percentage
        'nitrogen': 0.15,       # percentage
        'phosphorus': 0.08,     # percentage
        'potassium': 0.3        # percentage
    }
    
    # Previous crops
    previous_crops = ['wheat']
    
    recommendations = advisor.get_smart_recommendations(
        location_data, weather_data, soil_data, previous_crops
    )
    
    print(f"Top {len(recommendations)} crop recommendations:")
    for i, rec in enumerate(recommendations, 1):
        print(f"\n{i}. {rec['crop'].capitalize()}")
        print(f"   - Suitability Score: {rec['suitability_score']}")
        print(f"   - Market Potential: {rec['market_potential']}")
        print(f"   - Rotation Benefit: {rec['rotation_benefit']}")
        print(f"   - Planting Window: Month {rec['planting_info']['start_month']}-{rec['planting_info']['end_month']}")
        
        env_factors = rec['environmental_factors']
        print(f"   - Environmental Match: {env_factors}")
    
    # Test rotation suggestions
    print("\n4. Testing Crop Rotation Suggestions:")
    for crop in crops:
        suggestions = advisor.get_rotation_suggestions(crop)
        print(f"After {crop}: {', '.join(suggestions)}")
    
    print("\n✅ Crop Advisor Test Completed Successfully!")

if __name__ == "__main__":
    try:
        test_crop_advisor()
    except Exception as e:
        print(f"❌ Error during testing: {e}")
        import traceback
        traceback.print_exc()

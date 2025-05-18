import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.utils import get_region_for_coordinates

def test_region_detection():
    # Test cases with real coordinates in Uzbekistan
    test_cases = [
        # Tashkent region coordinates
        {"lat": 41.2995, "lon": 69.2834, "expected": "Tashkent"},
        
        # Andijan region coordinates
        {"lat": 40.7891, "lon": 72.3486, "expected": "Andijan"},
        
        # Bukhara region coordinates
        {"lat": 39.7689, "lon": 64.4456, "expected": "Bukhara"},
        
        # Samarkand region coordinates
        {"lat": 39.6543, "lon": 66.8945, "expected": "Samarkand"},
        
        # Fergana region coordinates
        {"lat": 40.3789, "lon": 71.7854, "expected": "Fergana"},
    ]

    print("Testing region detection...")
    for case in test_cases:
        result = get_region_for_coordinates(case["lat"], case["lon"])
        status = "✅" if result == case["expected"] else "❌"
        print(f"{status} Coordinates ({case['lat']}, {case['lon']}) -> Expected: {case['expected']}, Got: {result}")

if __name__ == "__main__":
    test_region_detection()

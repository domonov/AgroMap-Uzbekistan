"""Geo-utilities for region detection and coordinate handling."""
import json
import math
from typing import Dict, Tuple, Optional
import os

__all__ = ['get_region_for_coordinates', 'calculate_distance']

def load_regions_geojson() -> Dict:
    """Load the Uzbekistan regions GeoJSON file."""
    geojson_path = os.path.join(
        os.path.dirname(os.path.dirname(__file__)), 
        'static', 
        'data', 
        'uzbekistan_regions.geojson'
    )
    with open(geojson_path, 'r', encoding='utf-8') as f:
        return json.load(f)

def point_in_polygon(point: Tuple[float, float], polygon: list) -> bool:
    """
    Check if a point is inside a polygon using ray casting algorithm.
    
    Args:
        point: Tuple of (longitude, latitude)
        polygon: List of polygon coordinates

    Returns:
        bool: True if point is inside polygon
    """
    x, y = point
    inside = False
    j = len(polygon) - 1

    for i in range(len(polygon)):
        xi, yi = polygon[i]
        xj, yj = polygon[j]

        if ((yi > y) != (yj > y)) and (x < (xj - xi) * (y - yi) / (yj - yi) + xi):
            inside = not inside
        j = i

    return inside

def get_region_for_coordinates(latitude: float, longitude: float) -> Optional[str]:
    """
    Get the region name for given coordinates.
    
    Args:
        latitude: Latitude coordinate
        longitude: Longitude coordinate
        
    Returns:
        str: Region name if found, None otherwise
    """
    try:
        # Validate coordinates
        if not (-90 <= latitude <= 90) or not (-180 <= longitude <= 180):
            return None

        # Load GeoJSON data
        geojson_data = load_regions_geojson()
        
        # Check each region
        for feature in geojson_data['features']:
            if feature['geometry']['type'] == 'Polygon':
                coordinates = feature['geometry']['coordinates'][0]
                if point_in_polygon((longitude, latitude), coordinates):
                    return feature['properties']['name']
            elif feature['geometry']['type'] == 'MultiPolygon':
                for polygon in feature['geometry']['coordinates']:
                    if point_in_polygon((longitude, latitude), polygon[0]):
                        return feature['properties']['name']
        
        return None
    except Exception as e:
        print(f"Error detecting region: {e}")
        return None

def calculate_distance(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """
    Calculate the distance between two points using Haversine formula.
    
    Args:
        lat1: Latitude of first point
        lon1: Longitude of first point
        lat2: Latitude of second point
        lon2: Longitude of second point
        
    Returns:
        float: Distance in kilometers
    """
    R = 6371  # Earth's radius in kilometers

    lat1, lon1, lat2, lon2 = map(math.radians, [lat1, lon1, lat2, lon2])
    dlat = lat2 - lat1
    dlon = lon2 - lon1

    a = math.sin(dlat/2)**2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon/2)**2
    c = 2 * math.asin(math.sqrt(a))
    
    return R * c

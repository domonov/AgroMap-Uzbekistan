import requests
from flask import jsonify
import json
import logging
import re
import bleach
from shapely.geometry import Point, shape
from pathlib import Path
from urllib.parse import urlparse
import ipaddress

# 📌 Function: Get User Approximate Location via IP
def get_user_location(ip):
    """Fetch user's general location using IP parsing."""
    try:
        response = requests.get(f"https://ipinfo.io/{ip}/json")
        data = response.json()
        return {"latitude": float(data.get("loc", "").split(",")[0]), "longitude": float(data.get("loc", "").split(",")[1])} if "loc" in data else None
    except Exception as e:
        return {"error": f"Failed to retrieve location: {str(e)}"}

# 📌 Function: Validate Crop Submission Data
def validate_crop_data(data):
    """Ensure submitted crop data contains required fields."""
    required_fields = ["crop_type", "latitude", "longitude", "area_size"]
    return all(field in data and data[field] for field in required_fields)

# 📌 Function: Format Reports for JSON Response
def format_reports(report_list):
    """Format crop reports into JSON output for API calls."""
    return [{"crop": report.crop_type, "lat": report.latitude, "lon": report.longitude, "area": report.area_size} for report in report_list]

def generate_heatmap_data(reports):
    """Generate heatmap data from crop reports."""
    return [{
        "lat": report.latitude,
        "lng": report.longitude,
        "weight": report.area_size
    } for report in reports]

# Uzbekistan region boundaries (simplified for example)
REGION_BOUNDARIES = {
    "Tashkent": {
        "type": "Polygon",
        "coordinates": [[[69.1, 41.2], [69.4, 41.2], [69.4, 41.4], [69.1, 41.4], [69.1, 41.2]]]
    },
    # Add more regions with their boundary coordinates
    # This is a simplified example - in a real app, you would load this from a GeoJSON file
}

def load_region_boundaries():
    """Load Uzbekistan region boundaries from GeoJSON file."""
    geojson_path = Path(__file__).parent / 'static' / 'data' / 'uzbekistan_regions.geojson'
    with open(geojson_path, 'r') as f:
        return json.load(f)

def get_region_for_coordinates(lat, lon):
    """
    Determine which region a point falls within using proper point-in-polygon testing.

    Args:
        lat (float): Latitude of the point
        lon (float): Longitude of the point

    Returns:
        str: Name of the region or 'Unknown' if not found
    """
    point = Point(lon, lat)  # GeoJSON uses (longitude, latitude) order
    geojson_data = load_region_boundaries()

    for feature in geojson_data['features']:
        try:
            polygon = shape(feature['geometry'])
            # Check if point is contained or is very close to the polygon
            if polygon.contains(point) or polygon.distance(point) < 0.01:  # 0.01 degrees ≈ 1km
                return feature['properties']['name']
        except Exception as e:
            logging.warning(f"Error processing region {feature['properties'].get('name', 'unknown')}: {str(e)}")
            continue

    # If no exact match, find the closest region
    min_distance = float('inf')
    closest_region = None

    for feature in geojson_data['features']:
        try:
            polygon = shape(feature['geometry'])
            distance = polygon.distance(point)
            if distance < min_distance:
                min_distance = distance
                closest_region = feature['properties']['name']
        except Exception as e:
            continue

    # If we found a region within 0.1 degrees (≈ 11km), return it
    if closest_region and min_distance < 0.1:
        return closest_region

    return 'Unknown'

def get_region_boundaries(region_name):
    """
    Get the GeoJSON geometry for a specific region.

    Args:
        region_name (str): Name of the region

    Returns:
        dict: GeoJSON geometry object or None if not found
    """
    geojson_data = load_region_boundaries()

    for feature in geojson_data['features']:
        if feature['properties']['name'] == region_name:
            return feature['geometry']

    return None

# 📌 Prediction Model Functions

def predict_crop_yield(crop_type, field_id, weather_data, soil_data=None):
    """
    Predict crop yield based on crop type, field data, and weather conditions.

    Args:
        crop_type (str): Type of crop (e.g., wheat, cotton, rice)
        field_id (int): ID of the field
        weather_data (dict): Weather data including temperature, rainfall, etc.
        soil_data (dict, optional): Soil data if available

    Returns:
        dict: Prediction results including yield estimate and confidence score
    """
    from app.models import Field, CropCalendar, db

    # Get field data
    field = Field.query.get(field_id)
    if not field:
        return {"error": "Field not found"}

    # Get crop calendar data
    crop_calendar = CropCalendar.query.filter_by(
        field_id=field_id, 
        crop_type=crop_type
    ).order_by(CropCalendar.created_at.desc()).first()

    # Basic yield prediction model (simplified for demonstration)
    # In a real application, this would use machine learning models

    # Base yield values by crop type (tons per hectare)
    base_yields = {
        "wheat": 3.5,
        "cotton": 2.8,
        "rice": 4.2,
        "corn": 5.5,
        "vegetables": 15.0,
        "fruits": 12.0
    }

    # Default if crop type not in our database
    base_yield = base_yields.get(crop_type.lower(), 3.0)

    # Adjust for weather conditions
    weather_factor = 1.0

    # Temperature effect
    avg_temp = weather_data.get("avg_temperature", 20)
    if crop_type.lower() == "wheat":
        # Wheat prefers cooler temperatures
        if avg_temp < 5:
            weather_factor *= 0.7  # Too cold
        elif avg_temp > 25:
            weather_factor *= 0.8  # Too hot
        else:
            weather_factor *= 1.1  # Optimal
    elif crop_type.lower() == "cotton":
        # Cotton prefers warmer temperatures
        if avg_temp < 15:
            weather_factor *= 0.6  # Too cold
        elif avg_temp > 35:
            weather_factor *= 0.9  # Too hot
        else:
            weather_factor *= 1.2  # Optimal

    # Rainfall effect
    rainfall = weather_data.get("rainfall", 100)
    if rainfall < 50:
        weather_factor *= 0.8  # Too dry
    elif rainfall > 300:
        weather_factor *= 0.9  # Too wet
    else:
        weather_factor *= 1.1  # Optimal

    # Calculate predicted yield
    predicted_yield = base_yield * weather_factor * field.area_size

    # Calculate confidence score (simplified)
    # In a real model, this would be based on model statistics
    confidence_score = 0.7  # 70% confidence

    return {
        "crop_type": crop_type,
        "field_id": field_id,
        "field_name": field.name,
        "area_size": field.area_size,
        "predicted_yield": round(predicted_yield, 2),
        "yield_per_hectare": round(predicted_yield / field.area_size, 2),
        "confidence_score": confidence_score,
        "factors": {
            "weather_factor": round(weather_factor, 2),
            "base_yield": base_yield
        }
    }

def predict_disease_risk(crop_type, field_id, weather_data):
    """
    Predict disease risk for crops based on weather conditions.

    Args:
        crop_type (str): Type of crop
        field_id (int): ID of the field
        weather_data (dict): Weather data including humidity, temperature, etc.

    Returns:
        dict: Disease risk assessment with confidence score
    """
    from app.models import Field, db

    # Get field data
    field = Field.query.get(field_id)
    if not field:
        return {"error": "Field not found"}

    # Disease risk factors by crop type
    disease_factors = {
        "wheat": {
            "rust": {"humidity": 0.6, "temperature": 0.3, "rainfall": 0.1},
            "powdery_mildew": {"humidity": 0.7, "temperature": 0.2, "rainfall": 0.1}
        },
        "cotton": {
            "boll_rot": {"humidity": 0.5, "temperature": 0.3, "rainfall": 0.2},
            "leaf_spot": {"humidity": 0.4, "temperature": 0.4, "rainfall": 0.2}
        },
        "rice": {
            "blast": {"humidity": 0.5, "temperature": 0.4, "rainfall": 0.1},
            "blight": {"humidity": 0.6, "temperature": 0.3, "rainfall": 0.1}
        }
    }

    # Get disease factors for the crop type
    crop_diseases = disease_factors.get(crop_type.lower(), {})

    # If no disease data for this crop, return low risk
    if not crop_diseases:
        return {
            "crop_type": crop_type,
            "field_id": field_id,
            "field_name": field.name,
            "disease_risks": [{"disease": "general", "risk": 0.2, "confidence": 0.5}]
        }

    # Calculate disease risks
    disease_risks = []

    humidity = weather_data.get("humidity", 50) / 100  # Convert to 0-1 scale
    temperature = min(max(weather_data.get("avg_temperature", 20) / 40, 0), 1)  # Normalize to 0-1
    rainfall = min(weather_data.get("rainfall", 100) / 300, 1)  # Normalize to 0-1

    for disease, factors in crop_diseases.items():
        # Calculate weighted risk score
        risk_score = (
            factors["humidity"] * humidity +
            factors["temperature"] * temperature +
            factors["rainfall"] * rainfall
        )

        # Adjust to 0-1 scale
        risk_score = min(max(risk_score, 0), 1)

        disease_risks.append({
            "disease": disease,
            "risk": round(risk_score, 2),
            "confidence": 0.65,  # Simplified confidence score
            "factors": {
                "humidity_contribution": round(factors["humidity"] * humidity, 2),
                "temperature_contribution": round(factors["temperature"] * temperature, 2),
                "rainfall_contribution": round(factors["rainfall"] * rainfall, 2)
            }
        })

    return {
        "crop_type": crop_type,
        "field_id": field_id,
        "field_name": field.name,
        "disease_risks": disease_risks
    }

def generate_crop_recommendations(field_id, region=None):
    """
    Generate crop recommendations based on field location and regional data.

    Args:
        field_id (int): ID of the field
        region (str, optional): Region name if already known

    Returns:
        dict: Recommended crops with suitability scores
    """
    from app.models import Field, db

    # Get field data
    field = Field.query.get(field_id)
    if not field:
        return {"error": "Field not found"}

    # Determine region if not provided
    if not region:
        region = get_region_for_coordinates(field.latitude, field.longitude)

    # Regional crop suitability (simplified example)
    # In a real application, this would be based on historical data and soil analysis
    regional_suitability = {
        "Tashkent": {
            "wheat": 0.9,
            "vegetables": 0.85,
            "fruits": 0.8,
            "cotton": 0.7,
            "rice": 0.5,
            "corn": 0.75
        },
        "Samarkand": {
            "fruits": 0.9,
            "vegetables": 0.85,
            "wheat": 0.8,
            "cotton": 0.7,
            "corn": 0.8,
            "rice": 0.4
        },
        "Fergana": {
            "cotton": 0.95,
            "rice": 0.85,
            "vegetables": 0.8,
            "fruits": 0.75,
            "wheat": 0.7,
            "corn": 0.65
        }
    }

    # Get regional suitability or use default
    crop_suitability = regional_suitability.get(region, {
        "wheat": 0.7,
        "cotton": 0.7,
        "vegetables": 0.7,
        "fruits": 0.7,
        "corn": 0.7,
        "rice": 0.6
    })

    # Sort crops by suitability
    recommended_crops = [
        {"crop": crop, "suitability": score, "confidence": 0.75}
        for crop, score in sorted(crop_suitability.items(), key=lambda x: x[1], reverse=True)
    ]

    return {
        "field_id": field_id,
        "field_name": field.name,
        "region": region,
        "recommended_crops": recommended_crops
    }

# 📌 Data Processing Functions

def clean_weather_data(weather_data):
    """
    Clean and validate weather data for prediction models.

    Args:
        weather_data (dict): Raw weather data

    Returns:
        dict: Cleaned and validated weather data
    """
    cleaned_data = {}

    # Handle temperature
    if "temp" in weather_data:
        cleaned_data["avg_temperature"] = float(weather_data["temp"])
    elif "avg_temperature" in weather_data:
        cleaned_data["avg_temperature"] = float(weather_data["avg_temperature"])
    elif "temperature" in weather_data:
        cleaned_data["avg_temperature"] = float(weather_data["temperature"])
    else:
        cleaned_data["avg_temperature"] = 20.0  # Default value

    # Handle humidity
    if "humidity" in weather_data:
        cleaned_data["humidity"] = float(weather_data["humidity"])
    else:
        cleaned_data["humidity"] = 50.0  # Default value

    # Handle rainfall
    if "rain" in weather_data and isinstance(weather_data["rain"], dict) and "1h" in weather_data["rain"]:
        # OpenWeatherMap format
        cleaned_data["rainfall"] = float(weather_data["rain"]["1h"]) * 24  # Convert to daily
    elif "rainfall" in weather_data:
        cleaned_data["rainfall"] = float(weather_data["rainfall"])
    elif "precipitation" in weather_data:
        cleaned_data["rainfall"] = float(weather_data["precipitation"])
    else:
        cleaned_data["rainfall"] = 0.0  # Default value

    # Ensure values are within reasonable ranges
    cleaned_data["avg_temperature"] = max(min(cleaned_data["avg_temperature"], 50), -30)  # -30 to 50°C
    cleaned_data["humidity"] = max(min(cleaned_data["humidity"], 100), 0)  # 0-100%
    cleaned_data["rainfall"] = max(cleaned_data["rainfall"], 0)  # Non-negative

    return cleaned_data

def normalize_data(data, feature_ranges=None):
    """
    Normalize data to 0-1 range for machine learning models.

    Args:
        data (dict): Data to normalize
        feature_ranges (dict, optional): Min/max ranges for features

    Returns:
        dict: Normalized data
    """
    if feature_ranges is None:
        # Default feature ranges based on typical values
        feature_ranges = {
            "avg_temperature": (-30, 50),  # -30°C to 50°C
            "humidity": (0, 100),          # 0-100%
            "rainfall": (0, 500),          # 0-500mm
            "area_size": (0, 1000),        # 0-1000 hectares
            "yield": (0, 50),              # 0-50 tons/hectare
            "disease_risk": (0, 1)         # 0-1 probability
        }

    normalized = {}

    for key, value in data.items():
        if key in feature_ranges:
            min_val, max_val = feature_ranges[key]
            range_size = max_val - min_val
            if range_size > 0:
                normalized[key] = (float(value) - min_val) / range_size
            else:
                normalized[key] = 0.5  # Default if range is zero
        else:
            # Pass through values not in feature_ranges
            normalized[key] = value

    return normalized

def process_crop_data(crop_data):
    """
    Process and validate crop data for prediction models.

    Args:
        crop_data (dict): Raw crop data

    Returns:
        dict: Processed crop data
    """
    processed = {}

    # Standardize crop type (lowercase, remove extra spaces)
    if "crop_type" in crop_data:
        processed["crop_type"] = crop_data["crop_type"].lower().strip()

    # Process area size
    if "area_size" in crop_data:
        try:
            processed["area_size"] = float(crop_data["area_size"])
            # Ensure non-negative
            processed["area_size"] = max(processed["area_size"], 0)
        except (ValueError, TypeError):
            processed["area_size"] = 0.0

    # Process planting date
    if "planting_date" in crop_data:
        from datetime import datetime
        try:
            if isinstance(crop_data["planting_date"], str):
                # Try different date formats
                for fmt in ("%Y-%m-%d", "%d/%m/%Y", "%m/%d/%Y", "%d-%m-%Y", "%m-%d-%Y"):
                    try:
                        processed["planting_date"] = datetime.strptime(crop_data["planting_date"], fmt).date()
                        break
                    except ValueError:
                        continue
            else:
                processed["planting_date"] = crop_data["planting_date"]
        except Exception:
            # If all parsing fails, use None
            processed["planting_date"] = None

    # Process harvest date
    if "harvest_date" in crop_data:
        from datetime import datetime
        try:
            if isinstance(crop_data["harvest_date"], str):
                # Try different date formats
                for fmt in ("%Y-%m-%d", "%d/%m/%Y", "%m/%d/%Y", "%d-%m-%Y", "%m-%d-%Y"):
                    try:
                        processed["harvest_date"] = datetime.strptime(crop_data["harvest_date"], fmt).date()
                        break
                    except ValueError:
                        continue
            else:
                processed["harvest_date"] = crop_data["harvest_date"]
        except Exception:
            # If all parsing fails, use None
            processed["harvest_date"] = None

    return processed

def aggregate_field_data(field_id, start_date=None, end_date=None):
    """
    Aggregate historical data for a field for use in prediction models.

    Args:
        field_id (int): ID of the field
        start_date (date, optional): Start date for data aggregation
        end_date (date, optional): End date for data aggregation

    Returns:
        dict: Aggregated field data
    """
    from app.models import Field, CropReport, CropCalendar, Prediction, db
    from sqlalchemy import func
    from datetime import datetime, timedelta

    # Get field data
    field = Field.query.get(field_id)
    if not field:
        return {"error": "Field not found"}

    # Set default date range if not provided
    if not end_date:
        end_date = datetime.utcnow().date()
    if not start_date:
        start_date = end_date - timedelta(days=365)  # Default to 1 year of data

    # Get crop calendar entries for this field
    crop_calendars = CropCalendar.query.filter(
        CropCalendar.field_id == field_id,
        CropCalendar.planting_date >= start_date,
        CropCalendar.planting_date <= end_date
    ).all()

    # Get predictions for this field
    predictions = Prediction.query.filter(
        Prediction.field_id == field_id,
        Prediction.created_at >= start_date,
        Prediction.created_at <= end_date
    ).all()

    # Aggregate crop types and their frequency
    crop_counts = {}
    for calendar in crop_calendars:
        crop_type = calendar.crop_type.lower()
        if crop_type not in crop_counts:
            crop_counts[crop_type] = 0
        crop_counts[crop_type] += 1

    # Find most common crop
    most_common_crop = max(crop_counts.items(), key=lambda x: x[1])[0] if crop_counts else None

    # Aggregate prediction data
    prediction_data = {
        "yield_predictions": [],
        "disease_predictions": []
    }

    for pred in predictions:
        if pred.prediction_type == "yield":
            prediction_data["yield_predictions"].append({
                "crop_type": pred.crop_type,
                "value": pred.prediction_value,
                "confidence": pred.confidence_score,
                "date": pred.created_at
            })
        elif "disease_risk" in pred.prediction_type:
            prediction_data["disease_predictions"].append({
                "crop_type": pred.crop_type,
                "disease": pred.prediction_type.replace("disease_risk_", ""),
                "risk": pred.prediction_value,
                "confidence": pred.confidence_score,
                "date": pred.created_at
            })

    # Calculate average yield prediction if available
    avg_yield = None
    if prediction_data["yield_predictions"]:
        avg_yield = sum(p["value"] for p in prediction_data["yield_predictions"]) / len(prediction_data["yield_predictions"])

    # Get region
    region = get_region_for_coordinates(field.latitude, field.longitude)

    return {
        "field_id": field_id,
        "field_name": field.name,
        "region": region,
        "area_size": field.area_size,
        "most_common_crop": most_common_crop,
        "crop_history": [
            {
                "crop_type": calendar.crop_type,
                "planting_date": calendar.planting_date,
                "harvest_date": calendar.harvest_date
            } for calendar in crop_calendars
        ],
        "prediction_history": {
            "yield": {
                "average": avg_yield,
                "predictions": prediction_data["yield_predictions"]
            },
            "disease_risk": prediction_data["disease_predictions"]
        }
    }

def prepare_prediction_dataset(field_id, crop_type, prediction_type="yield"):
    """
    Prepare a dataset for prediction models by combining field, crop, and weather data.

    Args:
        field_id (int): ID of the field
        crop_type (str): Type of crop
        prediction_type (str): Type of prediction (yield, disease, etc.)

    Returns:
        dict: Prepared dataset for prediction models
    """
    from app.models import Field, CropCalendar, db
    import requests

    # Get field data
    field = Field.query.get(field_id)
    if not field:
        return {"error": "Field not found"}

    # Get crop calendar data
    crop_calendar = CropCalendar.query.filter_by(
        field_id=field_id, 
        crop_type=crop_type
    ).order_by(CropCalendar.created_at.desc()).first()

    # Get weather data
    try:
        api_key = "YOUR_OPENWEATHERMAP_API_KEY"  # Replace with your real API key
        url = f"https://api.openweathermap.org/data/2.5/weather?lat={field.latitude}&lon={field.longitude}&appid={api_key}&units=metric"
        resp = requests.get(url)
        if resp.status_code == 200:
            weather_data = resp.json()
            cleaned_weather = clean_weather_data(weather_data)
        else:
            # Use default weather data if API call fails
            cleaned_weather = {
                "avg_temperature": 20,
                "humidity": 50,
                "rainfall": 0
            }
    except Exception:
        # Use default weather data if API call fails
        cleaned_weather = {
            "avg_temperature": 20,
            "humidity": 50,
            "rainfall": 0
        }

    # Get region
    region = get_region_for_coordinates(field.latitude, field.longitude)

    # Prepare dataset
    dataset = {
        "field_id": field_id,
        "field_name": field.name,
        "region": region,
        "area_size": field.area_size,
        "crop_type": crop_type,
        "weather": cleaned_weather
    }

    # Add crop calendar data if available
    if crop_calendar:
        from datetime import datetime
        dataset["planting_date"] = crop_calendar.planting_date
        dataset["harvest_date"] = crop_calendar.harvest_date
        dataset["notes"] = crop_calendar.notes

        # Calculate days since planting
        if crop_calendar.planting_date:
            days_since_planting = (datetime.utcnow().date() - crop_calendar.planting_date).days
            dataset["days_since_planting"] = max(days_since_planting, 0)

    # Add historical data
    historical_data = aggregate_field_data(field_id)
    if "error" not in historical_data:
        dataset["historical_data"] = historical_data

    # Normalize numerical features for machine learning models
    features_to_normalize = {
        "area_size": dataset["area_size"],
        "avg_temperature": cleaned_weather["avg_temperature"],
        "humidity": cleaned_weather["humidity"],
        "rainfall": cleaned_weather["rainfall"]
    }

    if "days_since_planting" in dataset:
        features_to_normalize["days_since_planting"] = dataset["days_since_planting"]

    dataset["normalized_features"] = normalize_data(features_to_normalize)

    return dataset

# 📌 Statistical Analysis Functions

def calculate_basic_statistics(data_list):
    """
    Calculate basic statistical measures for a list of numerical values.

    Args:
        data_list (list): List of numerical values

    Returns:
        dict: Statistical measures including mean, median, min, max, etc.
    """
    if not data_list or not all(isinstance(x, (int, float)) for x in data_list):
        return {"error": "Invalid data for statistical analysis"}

    import statistics
    import math

    # Sort data for easier calculations
    sorted_data = sorted(data_list)
    n = len(sorted_data)

    # Basic statistics
    stats = {
        "count": n,
        "min": min(sorted_data),
        "max": max(sorted_data),
        "range": max(sorted_data) - min(sorted_data),
        "sum": sum(sorted_data),
        "mean": statistics.mean(sorted_data),
        "median": statistics.median(sorted_data)
    }

    # Add standard deviation and variance if we have enough data
    if n > 1:
        stats["variance"] = statistics.variance(sorted_data)
        stats["std_dev"] = statistics.stdev(sorted_data)
        stats["coefficient_of_variation"] = stats["std_dev"] / stats["mean"] if stats["mean"] != 0 else None

    # Add quartiles
    if n >= 4:
        stats["q1"] = sorted_data[n // 4] if n % 4 != 0 else (sorted_data[n // 4 - 1] + sorted_data[n // 4]) / 2
        stats["q3"] = sorted_data[3 * n // 4] if n % 4 != 0 else (sorted_data[3 * n // 4 - 1] + sorted_data[3 * n // 4]) / 2
        stats["iqr"] = stats["q3"] - stats["q1"]

    # Add skewness and kurtosis if we have enough data
    if n >= 3:
        # Calculate skewness (Pearson's moment coefficient of skewness)
        if stats.get("std_dev", 0) > 0:
            m3 = sum((x - stats["mean"]) ** 3 for x in sorted_data) / n
            stats["skewness"] = m3 / (stats["std_dev"] ** 3)
        else:
            stats["skewness"] = 0

        # Calculate kurtosis
        if n >= 4 and stats.get("std_dev", 0) > 0:
            m4 = sum((x - stats["mean"]) ** 4 for x in sorted_data) / n
            stats["kurtosis"] = m4 / (stats["std_dev"] ** 4) - 3  # Excess kurtosis (normal = 0)

    return stats

def analyze_crop_yields(crop_type=None, region=None, start_date=None, end_date=None):
    """
    Analyze crop yields across fields, optionally filtered by crop type, region, and date range.

    Args:
        crop_type (str, optional): Filter by crop type
        region (str, optional): Filter by region
        start_date (date, optional): Start date for analysis
        end_date (date, optional): End date for analysis

    Returns:
        dict: Statistical analysis of crop yields
    """
    from app.models import Prediction, Field, db
    from sqlalchemy import func
    from datetime import datetime, timedelta

    # Set default date range if not provided
    if not end_date:
        end_date = datetime.utcnow().date()
    if not start_date:
        start_date = end_date - timedelta(days=365)  # Default to 1 year of data

    # Base query for yield predictions
    query = db.session.query(
        Prediction.crop_type,
        Field.id.label('field_id'),
        Field.name.label('field_name'),
        Prediction.prediction_value.label('yield_value'),
        Prediction.confidence_score.label('confidence'),
        Prediction.created_at
    ).join(
        Field, Prediction.field_id == Field.id
    ).filter(
        Prediction.prediction_type == 'yield',
        Prediction.created_at >= start_date,
        Prediction.created_at <= end_date
    )

    # Apply filters
    if crop_type:
        query = query.filter(Prediction.crop_type == crop_type)

    if region:
        # This is a simplified approach - in a real app, you'd need to join with a regions table
        # or use a more sophisticated approach to filter by region
        fields_in_region = []
        all_fields = Field.query.all()
        for field in all_fields:
            if get_region_for_coordinates(field.latitude, field.longitude) == region:
                fields_in_region.append(field.id)

        if fields_in_region:
            query = query.filter(Field.id.in_(fields_in_region))
        else:
            return {"error": f"No fields found in region: {region}"}

    # Execute query
    results = query.all()

    if not results:
        return {"error": "No yield prediction data found matching the criteria"}

    # Extract yield values
    yield_values = [r.yield_value for r in results]

    # Calculate basic statistics
    stats = calculate_basic_statistics(yield_values)

    # Group by crop type
    crop_stats = {}
    for r in results:
        crop = r.crop_type
        if crop not in crop_stats:
            crop_stats[crop] = []
        crop_stats[crop].append(r.yield_value)

    # Calculate statistics for each crop type
    for crop, values in crop_stats.items():
        crop_stats[crop] = calculate_basic_statistics(values)

    # Return comprehensive analysis
    return {
        "overall_statistics": stats,
        "crop_statistics": crop_stats,
        "sample_size": len(results),
        "date_range": {
            "start": start_date.isoformat() if hasattr(start_date, 'isoformat') else start_date,
            "end": end_date.isoformat() if hasattr(end_date, 'isoformat') else end_date
        },
        "filters": {
            "crop_type": crop_type,
            "region": region
        }
    }

def analyze_disease_risk(crop_type=None, disease=None, region=None, start_date=None, end_date=None):
    """
    Analyze disease risk across fields, optionally filtered by crop type, disease, region, and date range.

    Args:
        crop_type (str, optional): Filter by crop type
        disease (str, optional): Filter by specific disease
        region (str, optional): Filter by region
        start_date (date, optional): Start date for analysis
        end_date (date, optional): End date for analysis

    Returns:
        dict: Statistical analysis of disease risks
    """
    from app.models import Prediction, Field, db
    from sqlalchemy import func
    from datetime import datetime, timedelta

    # Set default date range if not provided
    if not end_date:
        end_date = datetime.utcnow().date()
    if not start_date:
        start_date = end_date - timedelta(days=365)  # Default to 1 year of data

    # Base query for disease risk predictions
    query = db.session.query(
        Prediction.crop_type,
        Prediction.prediction_type.label('disease'),
        Field.id.label('field_id'),
        Field.name.label('field_name'),
        Prediction.prediction_value.label('risk'),
        Prediction.confidence_score.label('confidence'),
        Prediction.created_at
    ).join(
        Field, Prediction.field_id == Field.id
    ).filter(
        Prediction.prediction_type.like('disease_risk_%'),
        Prediction.created_at >= start_date,
        Prediction.created_at <= end_date
    )

    # Apply filters
    if crop_type:
        query = query.filter(Prediction.crop_type == crop_type)

    if disease:
        query = query.filter(Prediction.prediction_type == f'disease_risk_{disease}')

    if region:
        # This is a simplified approach - in a real app, you'd need to join with a regions table
        # or use a more sophisticated approach to filter by region
        fields_in_region = []
        all_fields = Field.query.all()
        for field in all_fields:
            if get_region_for_coordinates(field.latitude, field.longitude) == region:
                fields_in_region.append(field.id)

        if fields_in_region:
            query = query.filter(Field.id.in_(fields_in_region))
        else:
            return {"error": f"No fields found in region: {region}"}

    # Execute query
    results = query.all()

    if not results:
        return {"error": "No disease risk prediction data found matching the criteria"}

    # Extract risk values
    risks = [r.risk for r in results]

    # Calculate basic statistics
    stats = calculate_basic_statistics(risks)

    # Group by disease
    disease_stats = {}
    for r in results:
        disease_name = r.disease.replace('disease_risk_', '')
        if disease_name not in disease_stats:
            disease_stats[disease_name] = []
        disease_stats[disease_name].append(r.risk)

    # Calculate statistics for each disease
    for disease_name, values in disease_stats.items():
        disease_stats[disease_name] = calculate_basic_statistics(values)

    # Group by crop type
    crop_stats = {}
    for r in results:
        crop = r.crop_type
        if crop not in crop_stats:
            crop_stats[crop] = []
        crop_stats[crop].append(r.risk)

    # Calculate statistics for each crop type
    for crop, values in crop_stats.items():
        crop_stats[crop] = calculate_basic_statistics(values)

    # Return comprehensive analysis
    return {
        "overall_statistics": stats,
        "disease_statistics": disease_stats,
        "crop_statistics": crop_stats,
        "sample_size": len(results),
        "date_range": {
            "start": start_date.isoformat() if hasattr(start_date, 'isoformat') else start_date,
            "end": end_date.isoformat() if hasattr(end_date, 'isoformat') else end_date
        },
        "filters": {
            "crop_type": crop_type,
            "disease": disease,
            "region": region
        }
    }

def calculate_correlation(x_values, y_values):
    """
    Calculate Pearson correlation coefficient between two sets of values.

    Args:
        x_values (list): First set of numerical values
        y_values (list): Second set of numerical values

    Returns:
        float: Correlation coefficient (-1 to 1)
    """
    if len(x_values) != len(y_values) or len(x_values) < 2:
        return None

    import statistics
    import math

    n = len(x_values)

    # Calculate means
    mean_x = statistics.mean(x_values)
    mean_y = statistics.mean(y_values)

    # Calculate covariance and standard deviations
    covariance = sum((x - mean_x) * (y - mean_y) for x, y in zip(x_values, y_values)) / n
    std_dev_x = statistics.stdev(x_values)
    std_dev_y = statistics.stdev(y_values)

    # Calculate correlation coefficient
    if std_dev_x > 0 and std_dev_y > 0:
        correlation = covariance / (std_dev_x * std_dev_y)
        return correlation
    else:
        return 0  # No correlation if one of the variables has no variation

def analyze_weather_impact(crop_type, weather_factor="temperature", start_date=None, end_date=None):
    """
    Analyze the impact of weather factors on crop yields.

    Args:
        crop_type (str): Crop type to analyze
        weather_factor (str): Weather factor to analyze (temperature, humidity, rainfall)
        start_date (date, optional): Start date for analysis
        end_date (date, optional): End date for analysis

    Returns:
        dict: Analysis of weather impact on crop yields
    """
    from app.models import Prediction, db
    from datetime import datetime, timedelta
    import json

    # Set default date range if not provided
    if not end_date:
        end_date = datetime.utcnow().date()
    if not start_date:
        start_date = end_date - timedelta(days=365)  # Default to 1 year of data

    # Get yield predictions with weather data
    predictions = Prediction.query.filter(
        Prediction.crop_type == crop_type,
        Prediction.prediction_type == 'yield',
        Prediction.created_at >= start_date,
        Prediction.created_at <= end_date,
        Prediction.input_parameters.isnot(None)  # Ensure we have input parameters
    ).all()

    if not predictions:
        return {"error": f"No yield predictions found for crop type: {crop_type}"}

    # Extract weather values and yields
    weather_values = []
    yield_values = []

    for pred in predictions:
        # Parse input parameters (stored as JSON)
        params = pred.input_parameters
        if isinstance(params, str):
            try:
                params = json.loads(params)
            except:
                continue

        # Extract weather data
        weather_data = params.get('weather_data', {})

        # Get the specific weather factor
        if weather_factor == "temperature":
            weather_value = weather_data.get('avg_temperature')
        elif weather_factor == "humidity":
            weather_value = weather_data.get('humidity')
        elif weather_factor == "rainfall":
            weather_value = weather_data.get('rainfall')
        else:
            return {"error": f"Unsupported weather factor: {weather_factor}"}

        # Add to lists if we have valid data
        if weather_value is not None:
            weather_values.append(float(weather_value))
            yield_values.append(pred.prediction_value)

    if not weather_values or not yield_values:
        return {"error": f"No valid weather data found for factor: {weather_factor}"}

    # Calculate correlation
    correlation = calculate_correlation(weather_values, yield_values)

    # Calculate statistics for weather values
    weather_stats = calculate_basic_statistics(weather_values)

    # Calculate statistics for yields
    yield_stats = calculate_basic_statistics(yield_values)

    # Group data into bins for visualization
    bins = 5
    min_weather = min(weather_values)
    max_weather = max(weather_values)
    bin_size = (max_weather - min_weather) / bins if max_weather > min_weather else 1

    binned_data = {}
    for i in range(bins):
        bin_min = min_weather + i * bin_size
        bin_max = min_weather + (i + 1) * bin_size
        bin_key = f"{bin_min:.1f}-{bin_max:.1f}"
        binned_data[bin_key] = []

    for weather, yield_val in zip(weather_values, yield_values):
        for i in range(bins):
            bin_min = min_weather + i * bin_size
            bin_max = min_weather + (i + 1) * bin_size
            bin_key = f"{bin_min:.1f}-{bin_max:.1f}"
            if bin_min <= weather < bin_max or (i == bins - 1 and weather == max_weather):
                binned_data[bin_key].append(yield_val)
                break

    # Calculate average yield for each bin
    bin_averages = {}
    for bin_key, bin_yields in binned_data.items():
        if bin_yields:
            bin_averages[bin_key] = sum(bin_yields) / len(bin_yields)
        else:
            bin_averages[bin_key] = None

    # Return comprehensive analysis
    return {
        "crop_type": crop_type,
        "weather_factor": weather_factor,
        "correlation": correlation,
        "interpretation": interpret_correlation(correlation, weather_factor),
        "weather_statistics": weather_stats,
        "yield_statistics": yield_stats,
        "binned_analysis": bin_averages,
        "sample_size": len(yield_values),
        "date_range": {
            "start": start_date.isoformat() if hasattr(start_date, 'isoformat') else start_date,
            "end": end_date.isoformat() if hasattr(end_date, 'isoformat') else end_date
        }
    }

def interpret_correlation(correlation, factor):
    """
    Interpret the meaning of a correlation coefficient in agricultural terms.

    Args:
        correlation (float): Correlation coefficient (-1 to 1)
        factor (str): The factor being correlated

    Returns:
        str: Human-readable interpretation
    """
    if correlation is None:
        return "Insufficient data to calculate correlation."

    abs_corr = abs(correlation)

    if abs_corr < 0.1:
        strength = "negligible"
    elif abs_corr < 0.3:
        strength = "weak"
    elif abs_corr < 0.5:
        strength = "moderate"
    elif abs_corr < 0.7:
        strength = "strong"
    else:
        strength = "very strong"

    direction = "positive" if correlation > 0 else "negative"

    interpretations = {
        "temperature": {
            "positive": f"Higher temperatures are associated with higher yields, suggesting {factor} may be beneficial for growth.",
            "negative": f"Higher temperatures are associated with lower yields, suggesting {factor} may be causing stress or other negative effects."
        },
        "humidity": {
            "positive": f"Higher humidity is associated with higher yields, suggesting {factor} may be beneficial for growth.",
            "negative": f"Higher humidity is associated with lower yields, suggesting {factor} may be increasing disease risk or causing other negative effects."
        },
        "rainfall": {
            "positive": f"Higher rainfall is associated with higher yields, suggesting water availability is important for growth.",
            "negative": f"Higher rainfall is associated with lower yields, suggesting excessive water may be causing issues like root rot or nutrient leaching."
        }
    }

    factor_interpretation = interpretations.get(factor, {}).get(direction, "")

    if abs_corr < 0.1:
        return f"There is a {strength} correlation between {factor} and yield. This suggests {factor} has little to no impact on crop yield."

    return f"There is a {strength} {direction} correlation ({correlation:.2f}) between {factor} and yield. {factor_interpretation}"

# 📌 Prediction Validation Functions

def validate_prediction_model(model_id, test_data=None, validation_method="cross_validation", folds=5):
    """
    Validate a prediction model using various validation methods.

    Args:
        model_id (int): ID of the prediction model to validate
        test_data (list, optional): Test data for validation. If None, uses historical data.
        validation_method (str): Validation method to use (cross_validation, holdout, time_series)
        folds (int): Number of folds for cross-validation

    Returns:
        dict: Validation results including accuracy metrics
    """
    from app.models import PredictionModel, Prediction, db
    import random
    from datetime import datetime, timedelta

    # Get the prediction model
    model = PredictionModel.query.get(model_id)
    if not model:
        return {"error": "Model not found"}

    # Get historical predictions for this model
    predictions = Prediction.query.filter_by(model_id=model_id).all()
    if not predictions:
        return {"error": "No predictions found for this model"}

    # If test data is not provided, use historical data
    if test_data is None:
        # For yield predictions, we can compare against actual yields if available
        # For disease risk, we can check if disease actually occurred
        # For simplicity, we'll use a random subset of historical predictions as "actual" data
        test_data = []
        for pred in predictions:
            # In a real system, this would be actual observed data
            # Here we're simulating by adding some random variation to the prediction
            actual_value = pred.prediction_value * (1 + random.uniform(-0.2, 0.2))
            test_data.append({
                "prediction_id": pred.id,
                "actual_value": actual_value,
                "prediction_value": pred.prediction_value,
                "prediction_type": pred.prediction_type,
                "crop_type": pred.crop_type,
                "field_id": pred.field_id,
                "created_at": pred.created_at
            })

    # Perform validation based on the selected method
    if validation_method == "cross_validation":
        return perform_cross_validation(test_data, folds)
    elif validation_method == "holdout":
        return perform_holdout_validation(test_data)
    elif validation_method == "time_series":
        return perform_time_series_validation(test_data)
    else:
        return {"error": f"Unsupported validation method: {validation_method}"}

def perform_cross_validation(test_data, folds=5):
    """
    Perform k-fold cross-validation on the test data.

    Args:
        test_data (list): Test data for validation
        folds (int): Number of folds

    Returns:
        dict: Validation results
    """
    import random

    # Shuffle the data
    random.shuffle(test_data)

    # Split data into folds
    fold_size = len(test_data) // folds
    fold_data = []
    for i in range(folds):
        start_idx = i * fold_size
        end_idx = (i + 1) * fold_size if i < folds - 1 else len(test_data)
        fold_data.append(test_data[start_idx:end_idx])

    # Perform cross-validation
    metrics = {
        "mae": [],  # Mean Absolute Error
        "mse": [],  # Mean Squared Error
        "rmse": [], # Root Mean Squared Error
        "mape": [], # Mean Absolute Percentage Error
        "r2": []    # R-squared
    }

    for i in range(folds):
        # Use fold i as test set, rest as training set
        test_fold = fold_data[i]
        train_folds = [fold_data[j] for j in range(folds) if j != i]
        train_data = [item for fold in train_folds for item in fold]

        # Calculate metrics for this fold
        fold_metrics = calculate_prediction_metrics(test_fold)

        # Add metrics to overall results
        for key in metrics:
            metrics[key].append(fold_metrics[key])

    # Calculate average metrics across all folds
    avg_metrics = {key: sum(values) / len(values) for key, values in metrics.items()}

    # Calculate standard deviation of metrics
    std_metrics = {
        key: (sum((x - avg_metrics[key]) ** 2 for x in values) / len(values)) ** 0.5 
        for key, values in metrics.items()
    }

    return {
        "validation_method": "cross_validation",
        "folds": folds,
        "sample_size": len(test_data),
        "metrics": avg_metrics,
        "metrics_std": std_metrics,
        "fold_metrics": metrics
    }

def perform_holdout_validation(test_data, test_size=0.2):
    """
    Perform holdout validation by splitting data into training and test sets.

    Args:
        test_data (list): Test data for validation
        test_size (float): Proportion of data to use for testing

    Returns:
        dict: Validation results
    """
    import random

    # Shuffle the data
    random.shuffle(test_data)

    # Split data into training and test sets
    split_idx = int(len(test_data) * (1 - test_size))
    train_data = test_data[:split_idx]
    test_data = test_data[split_idx:]

    # Calculate metrics on test set
    metrics = calculate_prediction_metrics(test_data)

    return {
        "validation_method": "holdout",
        "test_size": test_size,
        "train_size": 1 - test_size,
        "train_samples": len(train_data),
        "test_samples": len(test_data),
        "metrics": metrics
    }

def perform_time_series_validation(test_data, train_ratio=0.7):
    """
    Perform time-series validation by splitting data chronologically.

    Args:
        test_data (list): Test data for validation
        train_ratio (float): Proportion of data to use for training

    Returns:
        dict: Validation results
    """
    # Sort data chronologically
    sorted_data = sorted(test_data, key=lambda x: x["created_at"])

    # Split data into training and test sets
    split_idx = int(len(sorted_data) * train_ratio)
    train_data = sorted_data[:split_idx]
    test_data = sorted_data[split_idx:]

    # Calculate metrics on test set
    metrics = calculate_prediction_metrics(test_data)

    return {
        "validation_method": "time_series",
        "train_ratio": train_ratio,
        "train_samples": len(train_data),
        "test_samples": len(test_data),
        "train_period": {
            "start": train_data[0]["created_at"].isoformat() if train_data else None,
            "end": train_data[-1]["created_at"].isoformat() if train_data else None
        },
        "test_period": {
            "start": test_data[0]["created_at"].isoformat() if test_data else None,
            "end": test_data[-1]["created_at"].isoformat() if test_data else None
        },
        "metrics": metrics
    }

def calculate_prediction_metrics(test_data):
    """
    Calculate various prediction accuracy metrics.

    Args:
        test_data (list): Test data with actual and predicted values

    Returns:
        dict: Metrics including MAE, MSE, RMSE, MAPE, R2
    """
    if not test_data:
        return {
            "mae": None,
            "mse": None,
            "rmse": None,
            "mape": None,
            "r2": None
        }

    # Extract actual and predicted values
    actual = [item["actual_value"] for item in test_data]
    predicted = [item["prediction_value"] for item in test_data]

    # Calculate Mean Absolute Error (MAE)
    mae = sum(abs(a - p) for a, p in zip(actual, predicted)) / len(actual)

    # Calculate Mean Squared Error (MSE)
    mse = sum((a - p) ** 2 for a, p in zip(actual, predicted)) / len(actual)

    # Calculate Root Mean Squared Error (RMSE)
    rmse = mse ** 0.5

    # Calculate Mean Absolute Percentage Error (MAPE)
    # Avoid division by zero
    mape_values = [abs((a - p) / a) * 100 for a, p in zip(actual, predicted) if a != 0]
    mape = sum(mape_values) / len(mape_values) if mape_values else None

    # Calculate R-squared (coefficient of determination)
    mean_actual = sum(actual) / len(actual)
    ss_total = sum((a - mean_actual) ** 2 for a in actual)
    ss_residual = sum((a - p) ** 2 for a, p in zip(actual, predicted))
    r2 = 1 - (ss_residual / ss_total) if ss_total != 0 else 0

    return {
        "mae": mae,
        "mse": mse,
        "rmse": rmse,
        "mape": mape,
        "r2": r2
    }

def validate_prediction_input(data, prediction_type="yield"):
    """
    Validate input data for prediction models.

    Args:
        data (dict): Input data for prediction
        prediction_type (str): Type of prediction (yield, disease, etc.)

    Returns:
        tuple: (is_valid, errors)
    """
    errors = []

    # Check required fields
    required_fields = ["field_id", "crop_type"]
    for field in required_fields:
        if field not in data or not data[field]:
            errors.append(f"Missing required field: {field}")

    # Validate field_id
    if "field_id" in data:
        try:
            field_id = int(data["field_id"])
            from app.models import Field
            field = Field.query.get(field_id)
            if not field:
                errors.append(f"Field with ID {field_id} not found")
        except (ValueError, TypeError):
            errors.append("field_id must be a valid integer")

    # Validate crop_type
    if "crop_type" in data:
        valid_crops = ["wheat", "cotton", "rice", "corn", "vegetables", "fruits"]
        if data["crop_type"].lower() not in valid_crops:
            errors.append(f"Invalid crop type. Must be one of: {', '.join(valid_crops)}")

    # Validate weather_data if provided
    if "weather_data" in data:
        weather_data = data["weather_data"]
        if not isinstance(weather_data, dict):
            errors.append("weather_data must be a dictionary")
        else:
            # Check for required weather fields based on prediction type
            if prediction_type == "yield":
                weather_fields = ["avg_temperature", "rainfall"]
            elif prediction_type == "disease":
                weather_fields = ["avg_temperature", "humidity", "rainfall"]
            else:
                weather_fields = []

            for field in weather_fields:
                if field not in weather_data:
                    errors.append(f"Missing required weather field: {field}")

    # Validate soil_data if provided
    if "soil_data" in data and data["soil_data"]:
        soil_data = data["soil_data"]
        if not isinstance(soil_data, dict):
            errors.append("soil_data must be a dictionary")

    # Return validation result
    is_valid = len(errors) == 0
    return (is_valid, errors)

def get_prediction_confidence(prediction_value, prediction_type, historical_data=None):
    """
    Calculate confidence score for a prediction based on historical accuracy.

    Args:
        prediction_value (float): The predicted value
        prediction_type (str): Type of prediction (yield, disease, etc.)
        historical_data (list, optional): Historical prediction data

    Returns:
        float: Confidence score (0-1)
    """
    from app.models import Prediction
    import math

    # Base confidence level
    base_confidence = 0.7

    # If no historical data provided, try to get from database
    if not historical_data:
        # Get similar predictions from database
        predictions = Prediction.query.filter_by(prediction_type=prediction_type).limit(100).all()

        if predictions:
            historical_data = []
            for pred in predictions:
                # In a real system, this would include actual observed values
                # Here we're simulating by adding some random variation
                import random
                actual_value = pred.prediction_value * (1 + random.uniform(-0.2, 0.2))
                historical_data.append({
                    "prediction_value": pred.prediction_value,
                    "actual_value": actual_value,
                    "confidence_score": pred.confidence_score
                })

    # If we have historical data, adjust confidence based on historical accuracy
    if historical_data:
        # Calculate mean absolute percentage error
        mape_values = []
        for item in historical_data:
            if item["actual_value"] != 0:
                mape = abs((item["actual_value"] - item["prediction_value"]) / item["actual_value"])
                mape_values.append(mape)

        if mape_values:
            avg_mape = sum(mape_values) / len(mape_values)
            # Convert MAPE to confidence score (higher MAPE = lower confidence)
            # Using an exponential decay function: confidence = base_confidence * e^(-k*MAPE)
            k = 2.0  # Decay factor
            historical_confidence = base_confidence * math.exp(-k * avg_mape)

            # Blend base confidence with historical confidence
            confidence = 0.3 * base_confidence + 0.7 * historical_confidence
        else:
            confidence = base_confidence
    else:
        confidence = base_confidence

    # Ensure confidence is in range [0, 1]
    confidence = max(0.0, min(1.0, confidence))

    return confidence

# 📌 Trend Analysis Functions

def analyze_prediction_trends(prediction_type="yield", crop_type=None, start_date=None, end_date=None, interval="month"):
    """
    Analyze trends in predictions over time.

    Args:
        prediction_type (str): Type of prediction to analyze (yield, disease_risk, etc.)
        crop_type (str, optional): Filter by crop type
        start_date (date, optional): Start date for analysis
        end_date (date, optional): End date for analysis
        interval (str): Time interval for grouping (day, week, month, year)

    Returns:
        dict: Trend analysis results
    """
    from app.models import Prediction, db
    from sqlalchemy import func
    from datetime import datetime, timedelta

    # Set default date range if not provided
    if not end_date:
        end_date = datetime.utcnow().date()
    if not start_date:
        start_date = end_date - timedelta(days=365)  # Default to 1 year of data

    # Base query
    query = Prediction.query.filter(
        Prediction.created_at >= start_date,
        Prediction.created_at <= end_date
    )

    # Apply filters
    if prediction_type == "yield":
        query = query.filter(Prediction.prediction_type == "yield")
    elif prediction_type == "disease":
        query = query.filter(Prediction.prediction_type.like("disease_risk_%"))
    else:
        query = query.filter(Prediction.prediction_type == prediction_type)

    if crop_type:
        query = query.filter(Prediction.crop_type == crop_type)

    # Group by time interval
    if interval == "day":
        grouping = func.date(Prediction.created_at)
    elif interval == "week":
        grouping = func.date_trunc("week", Prediction.created_at)
    elif interval == "year":
        grouping = func.date_trunc("year", Prediction.created_at)
    else:  # default to month
        grouping = func.date_trunc("month", Prediction.created_at)

    # Get aggregated data
    results = (
        query.with_entities(
            grouping.label("date"),
            func.avg(Prediction.prediction_value).label("avg_value"),
            func.min(Prediction.prediction_value).label("min_value"),
            func.max(Prediction.prediction_value).label("max_value"),
            func.stddev(Prediction.prediction_value).label("std_dev"),
            func.avg(Prediction.confidence_score).label("avg_confidence"),
            func.count().label("count")
        )
        .group_by(grouping)
        .order_by(grouping)
        .all()
    )

    # Format time series data
    time_series = []
    for result in results:
        time_series.append({
            "date": result.date.isoformat() if hasattr(result.date, 'isoformat') else str(result.date),
            "avg_value": float(result.avg_value) if result.avg_value is not None else None,
            "min_value": float(result.min_value) if result.min_value is not None else None,
            "max_value": float(result.max_value) if result.max_value is not None else None,
            "std_dev": float(result.std_dev) if result.std_dev is not None else None,
            "avg_confidence": float(result.avg_confidence) if result.avg_confidence is not None else None,
            "count": result.count
        })

    # Calculate trend statistics
    trend_stats = calculate_trend_statistics(time_series)

    return {
        "prediction_type": prediction_type,
        "crop_type": crop_type,
        "interval": interval,
        "date_range": {
            "start": start_date.isoformat() if hasattr(start_date, 'isoformat') else start_date,
            "end": end_date.isoformat() if hasattr(end_date, 'isoformat') else end_date
        },
        "time_series": time_series,
        "trend_statistics": trend_stats
    }

def calculate_trend_statistics(time_series):
    """
    Calculate statistics about a time series trend.

    Args:
        time_series (list): List of time series data points

    Returns:
        dict: Trend statistics
    """
    if not time_series:
        return {
            "trend_direction": "unknown",
            "trend_strength": 0,
            "volatility": 0,
            "seasonality": "unknown"
        }

    # Extract values for analysis
    values = [point["avg_value"] for point in time_series if point["avg_value"] is not None]
    if not values:
        return {
            "trend_direction": "unknown",
            "trend_strength": 0,
            "volatility": 0,
            "seasonality": "unknown"
        }

    # Calculate simple linear regression to determine trend
    n = len(values)
    x = list(range(n))
    sum_x = sum(x)
    sum_y = sum(values)
    sum_x_squared = sum(x_i ** 2 for x_i in x)
    sum_xy = sum(x_i * y_i for x_i, y_i in zip(x, values))

    # Calculate slope and intercept
    try:
        slope = (n * sum_xy - sum_x * sum_y) / (n * sum_x_squared - sum_x ** 2)
        intercept = (sum_y - slope * sum_x) / n
    except ZeroDivisionError:
        slope = 0
        intercept = sum_y / n if n > 0 else 0

    # Determine trend direction and strength
    if abs(slope) < 0.001:
        trend_direction = "stable"
        trend_strength = 0
    elif slope > 0:
        trend_direction = "increasing"
        trend_strength = min(1.0, abs(slope) * n / (max(values) - min(values)) if max(values) > min(values) else 0)
    else:
        trend_direction = "decreasing"
        trend_strength = min(1.0, abs(slope) * n / (max(values) - min(values)) if max(values) > min(values) else 0)

    # Calculate volatility (coefficient of variation)
    mean = sum(values) / n
    variance = sum((v - mean) ** 2 for v in values) / n
    std_dev = variance ** 0.5
    volatility = std_dev / mean if mean != 0 else 0

    # Detect seasonality (simplified)
    # In a real application, this would use more sophisticated methods like FFT or autocorrelation
    seasonality = "unknown"
    if n >= 12:  # Need at least a year of monthly data
        # Check for repeating patterns
        first_half = values[:n//2]
        second_half = values[n//2:]
        if len(first_half) == len(second_half):
            correlation = sum((a - mean) * (b - mean) for a, b in zip(first_half, second_half)) / (std_dev ** 2 * n / 2) if std_dev > 0 else 0
            if correlation > 0.7:
                seasonality = "strong"
            elif correlation > 0.3:
                seasonality = "moderate"
            elif correlation > 0.1:
                seasonality = "weak"
            else:
                seasonality = "none"

    return {
        "trend_direction": trend_direction,
        "trend_strength": trend_strength,
        "volatility": volatility,
        "seasonality": seasonality,
        "regression": {
            "slope": slope,
            "intercept": intercept,
            "predicted_values": [slope * i + intercept for i in range(n)]
        }
    }

def forecast_future_values(time_series, periods=6, method="linear"):
    """
    Forecast future values based on historical time series data.

    Args:
        time_series (list): List of time series data points
        periods (int): Number of periods to forecast
        method (str): Forecasting method (linear, exponential, average)

    Returns:
        list: Forecasted values
    """
    if not time_series:
        return []

    # Extract values for forecasting
    values = [point["avg_value"] for point in time_series if point["avg_value"] is not None]
    if not values:
        return []

    # Get dates for extending the forecast
    dates = [point["date"] for point in time_series]
    last_date = dates[-1] if dates else None

    # Generate future dates
    future_dates = []
    if last_date:
        from datetime import datetime, timedelta
        try:
            last_dt = datetime.fromisoformat(last_date)
            # Determine interval from existing data
            if len(dates) > 1:
                prev_dt = datetime.fromisoformat(dates[-2])
                interval = last_dt - prev_dt
            else:
                # Default to monthly
                interval = timedelta(days=30)

            # Generate future dates
            for i in range(1, periods + 1):
                future_dt = last_dt + interval * i
                future_dates.append(future_dt.isoformat())
        except (ValueError, TypeError):
            # If date parsing fails, use numeric indices
            future_dates = [f"Period {i+1}" for i in range(periods)]
    else:
        future_dates = [f"Period {i+1}" for i in range(periods)]

    # Apply forecasting method
    if method == "linear":
        # Simple linear regression
        n = len(values)
        x = list(range(n))
        sum_x = sum(x)
        sum_y = sum(values)
        sum_x_squared = sum(x_i ** 2 for x_i in x)
        sum_xy = sum(x_i * y_i for x_i, y_i in zip(x, values))

        try:
            slope = (n * sum_xy - sum_x * sum_y) / (n * sum_x_squared - sum_x ** 2)
            intercept = (sum_y - slope * sum_x) / n
            forecasted_values = [slope * (n + i) + intercept for i in range(1, periods + 1)]
        except ZeroDivisionError:
            # Fallback to average if regression fails
            avg = sum(values) / n
            forecasted_values = [avg] * periods

    elif method == "exponential":
        # Simple exponential smoothing
        alpha = 0.3  # Smoothing factor
        s = values[0]
        for value in values[1:]:
            s = alpha * value + (1 - alpha) * s

        forecasted_values = [s] * periods

    else:  # "average"
        # Simple moving average
        window = min(12, len(values))  # Use up to 12 most recent values
        recent_values = values[-window:]
        avg = sum(recent_values) / len(recent_values)
        forecasted_values = [avg] * periods

    # Combine dates and forecasted values
    forecast = []
    for i, value in enumerate(forecasted_values):
        forecast.append({
            "date": future_dates[i],
            "forecasted_value": value
        })

    return forecast

def compare_predictions_with_actuals(prediction_type="yield", start_date=None, end_date=None):
    """
    Compare predictions with actual values to evaluate accuracy over time.

    Args:
        prediction_type (str): Type of prediction to analyze
        start_date (date, optional): Start date for analysis
        end_date (date, optional): End date for analysis

    Returns:
        dict: Comparison results
    """
    from app.models import Prediction, db
    from datetime import datetime, timedelta
    import random  # For simulating actual values

    # Set default date range if not provided
    if not end_date:
        end_date = datetime.utcnow().date()
    if not start_date:
        start_date = end_date - timedelta(days=365)  # Default to 1 year of data

    # Get predictions for the specified type and date range
    predictions = Prediction.query.filter(
        Prediction.prediction_type == prediction_type,
        Prediction.created_at >= start_date,
        Prediction.created_at <= end_date
    ).all()

    if not predictions:
        return {
            "prediction_type": prediction_type,
            "date_range": {
                "start": start_date.isoformat() if hasattr(start_date, 'isoformat') else start_date,
                "end": end_date.isoformat() if hasattr(end_date, 'isoformat') else end_date
            },
            "comparisons": [],
            "accuracy_trend": [],
            "overall_accuracy": None
        }

    # In a real system, we would fetch actual observed values from a database
    # Here we're simulating by adding some random variation to the predictions
    comparisons = []
    for pred in predictions:
        # Simulate actual value with random variation
        actual_value = pred.prediction_value * (1 + random.uniform(-0.2, 0.2))

        # Calculate error metrics
        absolute_error = abs(actual_value - pred.prediction_value)
        percentage_error = (absolute_error / actual_value) * 100 if actual_value != 0 else None

        comparisons.append({
            "prediction_id": pred.id,
            "date": pred.created_at.isoformat(),
            "crop_type": pred.crop_type,
            "predicted_value": pred.prediction_value,
            "actual_value": actual_value,
            "absolute_error": absolute_error,
            "percentage_error": percentage_error,
            "confidence_score": pred.confidence_score
        })

    # Sort comparisons by date
    comparisons.sort(key=lambda x: x["date"])

    # Calculate accuracy trend over time
    accuracy_trend = []
    window_size = max(1, len(comparisons) // 10)  # Divide into ~10 windows

    for i in range(0, len(comparisons), window_size):
        window = comparisons[i:i+window_size]
        avg_date = window[len(window)//2]["date"]

        # Calculate average error for this window
        errors = [c["percentage_error"] for c in window if c["percentage_error"] is not None]
        if errors:
            avg_error = sum(errors) / len(errors)
            accuracy = max(0, 100 - avg_error)  # Convert error to accuracy percentage
        else:
            accuracy = None

        accuracy_trend.append({
            "date": avg_date,
            "accuracy": accuracy,
            "sample_size": len(window)
        })

    # Calculate overall accuracy
    all_errors = [c["percentage_error"] for c in comparisons if c["percentage_error"] is not None]
    overall_accuracy = max(0, 100 - sum(all_errors) / len(all_errors)) if all_errors else None

    return {
        "prediction_type": prediction_type,
        "date_range": {
            "start": start_date.isoformat() if hasattr(start_date, 'isoformat') else start_date,
            "end": end_date.isoformat() if hasattr(end_date, 'isoformat') else end_date
        },
        "comparisons": comparisons,
        "accuracy_trend": accuracy_trend,
        "overall_accuracy": overall_accuracy
    }

# 📌 Alert System Functions

def check_alert_conditions(user_id=None):
    """
    Check all alert rules and generate alerts if conditions are met.

    Args:
        user_id (int, optional): User ID to check rules for. If None, checks all users.

    Returns:
        list: New alerts generated
    """
    from app.models import AlertRule, Alert, Prediction, Field, db
    from datetime import datetime, timedelta

    # Get active alert rules
    query = AlertRule.query.filter(AlertRule.is_active == True)
    if user_id:
        query = query.filter(AlertRule.user_id == user_id)

    alert_rules = query.all()
    new_alerts = []

    for rule in alert_rules:
        # Get relevant data based on alert type
        if rule.alert_type == "yield":
            alerts = check_yield_alerts(rule)
        elif rule.alert_type == "disease":
            alerts = check_disease_alerts(rule)
        elif rule.alert_type == "weather":
            alerts = check_weather_alerts(rule)
        elif rule.alert_type == "anomaly":
            alerts = check_anomaly_alerts(rule)
        else:
            alerts = []

        # Add new alerts to database
        for alert in alerts:
            db.session.add(alert)
            new_alerts.append(alert)

    # Commit all new alerts
    if new_alerts:
        db.session.commit()

    return new_alerts

def check_yield_alerts(rule):
    """
    Check yield prediction alerts based on the rule.

    Args:
        rule (AlertRule): The alert rule to check

    Returns:
        list: Alerts generated
    """
    from app.models import Alert, Prediction, Field, db
    from datetime import datetime, timedelta

    alerts = []

    # Get recent yield predictions
    query = Prediction.query.filter(
        Prediction.prediction_type == "yield",
        Prediction.created_at >= datetime.utcnow() - timedelta(days=7)  # Last week
    )

    # Filter by field if specified
    if rule.field_id:
        query = query.filter(Prediction.field_id == rule.field_id)

    # Filter by crop type if specified
    if rule.crop_type:
        query = query.filter(Prediction.crop_type == rule.crop_type)

    predictions = query.all()

    for pred in predictions:
        # Check if condition is met
        condition_met = False

        if rule.condition_operator == ">":
            condition_met = pred.prediction_value > rule.condition_value
        elif rule.condition_operator == "<":
            condition_met = pred.prediction_value < rule.condition_value
        elif rule.condition_operator == "=":
            condition_met = abs(pred.prediction_value - rule.condition_value) < 0.001
        elif rule.condition_operator == ">=":
            condition_met = pred.prediction_value >= rule.condition_value
        elif rule.condition_operator == "<=":
            condition_met = pred.prediction_value <= rule.condition_value

        if condition_met:
            # Check if alert already exists
            existing_alert = Alert.query.filter(
                Alert.user_id == rule.user_id,
                Alert.field_id == pred.field_id,
                Alert.alert_type == "yield",
                Alert.created_at >= datetime.utcnow() - timedelta(days=1)  # Last 24 hours
            ).first()

            if not existing_alert:
                # Create new alert
                field = Field.query.get(pred.field_id)
                field_name = field.name if field else f"Field #{pred.field_id}"

                message = f"Yield alert: {rule.condition_operator} {rule.condition_value} tons/ha"
                if rule.condition_operator == "<" or rule.condition_operator == "<=":
                    message = f"Low yield prediction of {pred.prediction_value:.2f} tons/ha for {pred.crop_type} in {field_name}"
                elif rule.condition_operator == ">" or rule.condition_operator == ">=":
                    message = f"High yield prediction of {pred.prediction_value:.2f} tons/ha for {pred.crop_type} in {field_name}"

                alert = Alert(
                    user_id=rule.user_id,
                    field_id=pred.field_id,
                    alert_type="yield",
                    severity=rule.severity,
                    message=message,
                    details={
                        "prediction_id": pred.id,
                        "prediction_value": pred.prediction_value,
                        "confidence_score": pred.confidence_score,
                        "crop_type": pred.crop_type,
                        "rule_id": rule.id,
                        "condition": f"{rule.condition_operator} {rule.condition_value}"
                    },
                    is_read=False,
                    created_at=datetime.utcnow(),
                    expires_at=datetime.utcnow() + timedelta(days=7)  # Expires in 7 days
                )

                alerts.append(alert)

    return alerts

def check_disease_alerts(rule):
    """
    Check disease risk alerts based on the rule.

    Args:
        rule (AlertRule): The alert rule to check

    Returns:
        list: Alerts generated
    """
    from app.models import Alert, Prediction, Field, db
    from datetime import datetime, timedelta

    alerts = []

    # Get recent disease risk predictions
    query = Prediction.query.filter(
        Prediction.prediction_type.like("disease_risk_%"),
        Prediction.created_at >= datetime.utcnow() - timedelta(days=7)  # Last week
    )

    # Filter by field if specified
    if rule.field_id:
        query = query.filter(Prediction.field_id == rule.field_id)

    # Filter by crop type if specified
    if rule.crop_type:
        query = query.filter(Prediction.crop_type == rule.crop_type)

    predictions = query.all()

    for pred in predictions:
        # Extract disease name from prediction_type
        disease_name = pred.prediction_type.replace("disease_risk_", "")

        # Check if condition is met
        condition_met = False

        if rule.condition_operator == ">":
            condition_met = pred.prediction_value > rule.condition_value
        elif rule.condition_operator == "<":
            condition_met = pred.prediction_value < rule.condition_value
        elif rule.condition_operator == "=":
            condition_met = abs(pred.prediction_value - rule.condition_value) < 0.001
        elif rule.condition_operator == ">=":
            condition_met = pred.prediction_value >= rule.condition_value
        elif rule.condition_operator == "<=":
            condition_met = pred.prediction_value <= rule.condition_value

        if condition_met:
            # Check if alert already exists
            existing_alert = Alert.query.filter(
                Alert.user_id == rule.user_id,
                Alert.field_id == pred.field_id,
                Alert.alert_type == "disease",
                Alert.details.contains({"disease": disease_name}),
                Alert.created_at >= datetime.utcnow() - timedelta(days=1)  # Last 24 hours
            ).first()

            if not existing_alert:
                # Create new alert
                field = Field.query.get(pred.field_id)
                field_name = field.name if field else f"Field #{pred.field_id}"

                risk_percentage = pred.prediction_value * 100
                message = f"High disease risk ({risk_percentage:.1f}%) for {disease_name} in {pred.crop_type} at {field_name}"

                alert = Alert(
                    user_id=rule.user_id,
                    field_id=pred.field_id,
                    alert_type="disease",
                    severity=rule.severity,
                    message=message,
                    details={
                        "prediction_id": pred.id,
                        "disease": disease_name,
                        "risk_value": pred.prediction_value,
                        "confidence_score": pred.confidence_score,
                        "crop_type": pred.crop_type,
                        "rule_id": rule.id,
                        "condition": f"{rule.condition_operator} {rule.condition_value}"
                    },
                    is_read=False,
                    created_at=datetime.utcnow(),
                    expires_at=datetime.utcnow() + timedelta(days=7)  # Expires in 7 days
                )

                alerts.append(alert)

    return alerts

def check_weather_alerts(rule):
    """
    Check weather alerts based on the rule.

    Args:
        rule (AlertRule): The alert rule to check

    Returns:
        list: Alerts generated
    """
    from app.models import Alert, Field, db
    from datetime import datetime, timedelta
    import requests

    alerts = []

    # Get field to check weather for
    if rule.field_id:
        fields = [Field.query.get(rule.field_id)]
    else:
        # If no specific field, check all fields for this user
        fields = Field.query.filter_by(owner_id=rule.user_id).all()

    for field in fields:
        if not field:
            continue

        # Get weather data for field location
        try:
            api_key = "YOUR_OPENWEATHERMAP_API_KEY"  # Replace with your real API key
            url = f"https://api.openweathermap.org/data/2.5/weather?lat={field.latitude}&lon={field.longitude}&appid={api_key}&units=metric"
            resp = requests.get(url)

            if resp.status_code != 200:
                continue

            weather_data = resp.json()

            # Extract relevant weather parameter based on condition type
            weather_value = None
            weather_param = ""

            if rule.condition_type == "temperature":
                weather_value = weather_data["main"]["temp"]
                weather_param = "temperature"
            elif rule.condition_type == "humidity":
                weather_value = weather_data["main"]["humidity"]
                weather_param = "humidity"
            elif rule.condition_type == "wind":
                weather_value = weather_data["wind"]["speed"]
                weather_param = "wind speed"
            elif rule.condition_type == "rainfall" and "rain" in weather_data:
                weather_value = weather_data["rain"].get("1h", 0) * 24  # Convert to daily
                weather_param = "rainfall"

            if weather_value is None:
                continue

            # Check if condition is met
            condition_met = False

            if rule.condition_operator == ">":
                condition_met = weather_value > rule.condition_value
            elif rule.condition_operator == "<":
                condition_met = weather_value < rule.condition_value
            elif rule.condition_operator == "=":
                condition_met = abs(weather_value - rule.condition_value) < 0.001
            elif rule.condition_operator == ">=":
                condition_met = weather_value >= rule.condition_value
            elif rule.condition_operator == "<=":
                condition_met = weather_value <= rule.condition_value

            if condition_met:
                # Check if alert already exists
                existing_alert = Alert.query.filter(
                    Alert.user_id == rule.user_id,
                    Alert.field_id == field.id,
                    Alert.alert_type == "weather",
                    Alert.details.contains({"weather_param": weather_param}),
                    Alert.created_at >= datetime.utcnow() - timedelta(hours=6)  # Last 6 hours
                ).first()

                if not existing_alert:
                    # Create new alert
                    message = f"Weather alert: {weather_param} is {weather_value} {get_weather_unit(weather_param)} at {field.name}"

                    alert = Alert(
                        user_id=rule.user_id,
                        field_id=field.id,
                        alert_type="weather",
                        severity=rule.severity,
                        message=message,
                        details={
                            "weather_param": weather_param,
                            "weather_value": weather_value,
                            "location": {"lat": field.latitude, "lon": field.longitude},
                            "rule_id": rule.id,
                            "condition": f"{rule.condition_operator} {rule.condition_value}"
                        },
                        is_read=False,
                        created_at=datetime.utcnow(),
                        expires_at=datetime.utcnow() + timedelta(days=1)  # Expires in 1 day
                    )

                    alerts.append(alert)

        except Exception as e:
            # Log error and continue
            print(f"Error checking weather for field {field.id}: {str(e)}")
            continue

    return alerts

def check_anomaly_alerts(rule):
    """
    Check for anomalies in predictions or measurements.

    Args:
        rule (AlertRule): The alert rule to check

    Returns:
        list: Alerts generated
    """
    from app.models import Alert, Prediction, Field, db
    from datetime import datetime, timedelta

    alerts = []

    # Get historical predictions for comparison
    if rule.condition_type == "yield_anomaly":
        prediction_type = "yield"
    elif rule.condition_type == "disease_anomaly":
        prediction_type = "disease_risk_%"
    else:
        return []

    # Get fields to check
    if rule.field_id:
        fields = [Field.query.get(rule.field_id)]
    else:
        # If no specific field, check all fields for this user
        fields = Field.query.filter_by(owner_id=rule.user_id).all()

    for field in fields:
        if not field:
            continue

        # Get recent predictions
        recent_query = Prediction.query.filter(
            Prediction.field_id == field.id,
            Prediction.prediction_type.like(prediction_type),
            Prediction.created_at >= datetime.utcnow() - timedelta(days=7)  # Last week
        )

        # Filter by crop type if specified
        if rule.crop_type:
            recent_query = recent_query.filter(Prediction.crop_type == rule.crop_type)

        recent_predictions = recent_query.all()

        # Get historical predictions
        historical_query = Prediction.query.filter(
            Prediction.field_id == field.id,
            Prediction.prediction_type.like(prediction_type),
            Prediction.created_at < datetime.utcnow() - timedelta(days=7),  # Older than a week
            Prediction.created_at >= datetime.utcnow() - timedelta(days=90)  # Last 90 days
        )

        # Filter by crop type if specified
        if rule.crop_type:
            historical_query = historical_query.filter(Prediction.crop_type == rule.crop_type)

        historical_predictions = historical_query.all()

        if not recent_predictions or not historical_predictions:
            continue

        # Calculate average historical value
        historical_avg = sum(p.prediction_value for p in historical_predictions) / len(historical_predictions)

        for pred in recent_predictions:
            # Calculate percent change from historical average
            percent_change = ((pred.prediction_value - historical_avg) / historical_avg) * 100

            # Check if anomaly threshold is exceeded
            if abs(percent_change) >= rule.condition_value:
                # Check if alert already exists
                existing_alert = Alert.query.filter(
                    Alert.user_id == rule.user_id,
                    Alert.field_id == field.id,
                    Alert.alert_type == "anomaly",
                    Alert.details.contains({"prediction_id": pred.id}),
                    Alert.created_at >= datetime.utcnow() - timedelta(days=1)  # Last 24 hours
                ).first()

                if not existing_alert:
                    # Create new alert
                    direction = "increase" if percent_change > 0 else "decrease"
                    alert_type_name = "yield" if prediction_type == "yield" else "disease risk"

                    message = f"Anomaly detected: {abs(percent_change):.1f}% {direction} in {alert_type_name} for {pred.crop_type} in {field.name}"

                    alert = Alert(
                        user_id=rule.user_id,
                        field_id=field.id,
                        alert_type="anomaly",
                        severity=rule.severity,
                        message=message,
                        details={
                            "prediction_id": pred.id,
                            "prediction_type": pred.prediction_type,
                            "prediction_value": pred.prediction_value,
                            "historical_avg": historical_avg,
                            "percent_change": percent_change,
                            "crop_type": pred.crop_type,
                            "rule_id": rule.id,
                            "condition": f"change >= {rule.condition_value}%"
                        },
                        is_read=False,
                        created_at=datetime.utcnow(),
                        expires_at=datetime.utcnow() + timedelta(days=7)  # Expires in 7 days
                    )

                    alerts.append(alert)

    return alerts

def get_weather_unit(param):
    """
    Get the unit for a weather parameter.

    Args:
        param (str): Weather parameter

    Returns:
        str: Unit string
    """
    units = {
        "temperature": "°C",
        "humidity": "%",
        "wind": "m/s",
        "rainfall": "mm",
        "pressure": "hPa"
    }

    return units.get(param, "")

def get_user_alerts(user_id, include_read=False, limit=50):
    """
    Get alerts for a user.

    Args:
        user_id (int): User ID
        include_read (bool): Whether to include read alerts
        limit (int): Maximum number of alerts to return

    Returns:
        list: Alerts for the user
    """
    from app.models import Alert, db
    from datetime import datetime

    # Query alerts for user
    query = Alert.query.filter(
        Alert.user_id == user_id,
        Alert.expires_at > datetime.utcnow()  # Only non-expired alerts
    )

    if not include_read:
        query = query.filter(Alert.is_read == False)

    # Order by created_at (newest first) and limit
    alerts = query.order_by(Alert.created_at.desc()).limit(limit).all()

    return alerts

def mark_alert_as_read(alert_id, user_id):
    """
    Mark an alert as read.

    Args:
        alert_id (int): Alert ID
        user_id (int): User ID (for security check)

    Returns:
        bool: Success status
    """
    from app.models import Alert, db

    # Get the alert
    alert = Alert.query.get(alert_id)

    # Check if alert exists and belongs to the user
    if not alert or alert.user_id != user_id:
        return False

    # Mark as read
    alert.is_read = True

    try:
        db.session.commit()
        return True
    except Exception:
        db.session.rollback()
        return False

# ===== Input Validation Utilities =====

def sanitize_string(input_str, max_length=255, allow_html=False):
    """
    Sanitize a string input to prevent XSS attacks.

    Args:
        input_str (str): The input string to sanitize
        max_length (int): Maximum allowed length
        allow_html (bool): Whether to allow some HTML tags

    Returns:
        str: Sanitized string
    """
    if input_str is None:
        return None

    # Convert to string if not already
    if not isinstance(input_str, str):
        input_str = str(input_str)

    # Truncate if too long
    if len(input_str) > max_length:
        input_str = input_str[:max_length]

    if allow_html:
        # Allow only specific HTML tags and attributes
        allowed_tags = ['a', 'b', 'i', 'strong', 'em', 'p', 'br', 'ul', 'ol', 'li', 'span']
        allowed_attrs = {
            'a': ['href', 'title', 'target'],
            'span': ['class'],
            '*': ['class']
        }
        return bleach.clean(input_str, tags=allowed_tags, attributes=allowed_attrs, strip=True)
    else:
        # Strip all HTML tags
        return bleach.clean(input_str, tags=[], attributes={}, strip=True)

def validate_email(email):
    """
    Validate an email address format.

    Args:
        email (str): Email address to validate

    Returns:
        bool: True if valid, False otherwise
    """
    if not email or not isinstance(email, str):
        return False

    # Basic email regex pattern
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return bool(re.match(pattern, email))

def validate_url(url, allowed_schemes=None, allowed_domains=None):
    """
    Validate a URL for security.

    Args:
        url (str): URL to validate
        allowed_schemes (list): List of allowed URL schemes (e.g., ['http', 'https'])
        allowed_domains (list): List of allowed domains

    Returns:
        bool: True if valid, False otherwise
    """
    if not url or not isinstance(url, str):
        return False

    if allowed_schemes is None:
        allowed_schemes = ['http', 'https']

    try:
        parsed = urlparse(url)

        # Check scheme
        if parsed.scheme not in allowed_schemes:
            return False

        # Check domain if restricted
        if allowed_domains and parsed.netloc not in allowed_domains:
            return False

        # Basic URL validation
        return bool(parsed.netloc and parsed.scheme)
    except:
        return False

def validate_integer(value, min_value=None, max_value=None):
    """
    Validate an integer value within specified range.

    Args:
        value: Value to validate
        min_value (int): Minimum allowed value
        max_value (int): Maximum allowed value

    Returns:
        bool: True if valid, False otherwise
    """
    try:
        int_value = int(value)

        if min_value is not None and int_value < min_value:
            return False

        if max_value is not None and int_value > max_value:
            return False

        return True
    except (ValueError, TypeError):
        return False

def validate_float(value, min_value=None, max_value=None):
    """
    Validate a float value within specified range.

    Args:
        value: Value to validate
        min_value (float): Minimum allowed value
        max_value (float): Maximum allowed value

    Returns:
        bool: True if valid, False otherwise
    """
    try:
        float_value = float(value)

        if min_value is not None and float_value < min_value:
            return False

        if max_value is not None and float_value > max_value:
            return False

        return True
    except (ValueError, TypeError):
        return False

def validate_date(date_str, format="%Y-%m-%d"):
    """
    Validate a date string format.

    Args:
        date_str (str): Date string to validate
        format (str): Expected date format

    Returns:
        bool: True if valid, False otherwise
    """
    from datetime import datetime

    if not date_str or not isinstance(date_str, str):
        return False

    try:
        datetime.strptime(date_str, format)
        return True
    except ValueError:
        return False

def validate_ip_address(ip):
    """
    Validate an IP address (IPv4 or IPv6).

    Args:
        ip (str): IP address to validate

    Returns:
        bool: True if valid, False otherwise
    """
    if not ip or not isinstance(ip, str):
        return False

    try:
        ipaddress.ip_address(ip)
        return True
    except ValueError:
        return False

def validate_coordinates(lat, lon):
    """
    Validate geographic coordinates.

    Args:
        lat (float): Latitude
        lon (float): Longitude

    Returns:
        bool: True if valid, False otherwise
    """
    try:
        lat_float = float(lat)
        lon_float = float(lon)

        # Check latitude range (-90 to 90)
        if lat_float < -90 or lat_float > 90:
            return False

        # Check longitude range (-180 to 180)
        if lon_float < -180 or lon_float > 180:
            return False

        return True
    except (ValueError, TypeError):
        return False

def validate_json(json_str):
    """
    Validate a JSON string.

    Args:
        json_str (str): JSON string to validate

    Returns:
        bool: True if valid, False otherwise
    """
    if not json_str:
        return False

    try:
        # Try to parse the JSON
        if isinstance(json_str, str):
            json.loads(json_str)
        else:
            # If already an object, check if it's serializable
            json.dumps(json_str)
        return True
    except (ValueError, TypeError):
        return False

def validate_file_extension(filename, allowed_extensions):
    """
    Validate file extension against a list of allowed extensions.

    Args:
        filename (str): Filename to validate
        allowed_extensions (list): List of allowed extensions (e.g., ['.jpg', '.png'])

    Returns:
        bool: True if valid, False otherwise
    """
    if not filename or not isinstance(filename, str):
        return False

    # Get file extension
    ext = Path(filename).suffix.lower()

    return ext in allowed_extensions

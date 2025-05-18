# AgroMap API Documentation

## Overview

The AgroMap API provides programmatic access to agricultural data, analytics, and mapping features. This documentation covers all available endpoints, authentication methods, and example usage.

## Base URL

All API endpoints are relative to the base URL:

```
https://api.agromap-uzbekistan.org/v1
```

## Authentication

### API Key Authentication

Most API endpoints require authentication using an API key. Include your API key in the request header:

```
Authorization: Bearer YOUR_API_KEY
```

### Obtaining an API Key

1. Log in to your AgroMap account
2. Navigate to Profile > API Access
3. Generate a new API key
4. Store your API key securely - it will only be shown once

## Rate Limiting

API requests are subject to rate limiting to ensure fair usage:

- 1000 requests per day
- 100 requests per hour
- 10 requests per minute

Rate limit headers are included in all API responses:

```
X-RateLimit-Limit: 1000
X-RateLimit-Remaining: 999
X-RateLimit-Reset: 1628607988
```

## Response Format

All API responses are returned in JSON format with the following structure:

```json
{
  "status": "success",
  "data": { ... },
  "meta": {
    "pagination": { ... }
  }
}
```

For error responses:

```json
{
  "status": "error",
  "error": {
    "code": "error_code",
    "message": "Error message"
  }
}
```

## Error Codes

| Code | Description |
|------|-------------|
| 400 | Bad Request - The request was malformed |
| 401 | Unauthorized - Authentication failed |
| 403 | Forbidden - You don't have permission |
| 404 | Not Found - Resource doesn't exist |
| 429 | Too Many Requests - Rate limit exceeded |
| 500 | Server Error - Something went wrong on our end |

## Endpoints

### Crops

#### List Crops

```
GET /crops
```

Query Parameters:

| Parameter | Type | Description |
|-----------|------|-------------|
| region | string | Filter by region name |
| type | string | Filter by crop type |
| page | integer | Page number (default: 1) |
| limit | integer | Results per page (default: 20, max: 100) |

Example Response:

```json
{
  "status": "success",
  "data": [
    {
      "id": 1,
      "name": "Cotton",
      "type": "fiber",
      "region": "Tashkent",
      "area_hectares": 5000,
      "yield_per_hectare": 3.2,
      "planting_date": "2023-03-15",
      "harvest_date": "2023-09-20"
    },
    ...
  ],
  "meta": {
    "pagination": {
      "total": 245,
      "pages": 13,
      "page": 1,
      "limit": 20
    }
  }
}
```

#### Get Crop Details

```
GET /crops/{id}
```

Path Parameters:

| Parameter | Type | Description |
|-----------|------|-------------|
| id | integer | Crop ID |

Example Response:

```json
{
  "status": "success",
  "data": {
    "id": 1,
    "name": "Cotton",
    "type": "fiber",
    "region": "Tashkent",
    "area_hectares": 5000,
    "yield_per_hectare": 3.2,
    "planting_date": "2023-03-15",
    "harvest_date": "2023-09-20",
    "soil_type": "Loamy",
    "irrigation_type": "Drip",
    "fertilizer_usage": {
      "nitrogen": "120kg/ha",
      "phosphorus": "80kg/ha",
      "potassium": "60kg/ha"
    },
    "weather_data": {
      "average_temperature": 25.3,
      "total_rainfall": 320.5,
      "sunshine_hours": 1450
    }
  }
}
```

#### Create Crop

```
POST /crops
```

Request Body:

```json
{
  "name": "Wheat",
  "type": "grain",
  "region": "Samarkand",
  "area_hectares": 3500,
  "planting_date": "2023-10-15",
  "expected_harvest_date": "2024-06-10",
  "soil_type": "Clay loam",
  "irrigation_type": "Sprinkler"
}
```

Required fields: `name`, `type`, `region`, `area_hectares`, `planting_date`

Example Response:

```json
{
  "status": "success",
  "data": {
    "id": 246,
    "name": "Wheat",
    "type": "grain",
    "region": "Samarkand",
    "area_hectares": 3500,
    "planting_date": "2023-10-15",
    "expected_harvest_date": "2024-06-10",
    "soil_type": "Clay loam",
    "irrigation_type": "Sprinkler",
    "created_at": "2023-10-10T14:30:22Z"
  }
}
```

#### Update Crop

```
PUT /crops/{id}
```

Path Parameters:

| Parameter | Type | Description |
|-----------|------|-------------|
| id | integer | Crop ID |

Request Body:

```json
{
  "area_hectares": 3800,
  "expected_harvest_date": "2024-06-15",
  "notes": "Increased area due to favorable conditions"
}
```

Example Response:

```json
{
  "status": "success",
  "data": {
    "id": 246,
    "name": "Wheat",
    "type": "grain",
    "region": "Samarkand",
    "area_hectares": 3800,
    "planting_date": "2023-10-15",
    "expected_harvest_date": "2024-06-15",
    "soil_type": "Clay loam",
    "irrigation_type": "Sprinkler",
    "notes": "Increased area due to favorable conditions",
    "updated_at": "2023-10-12T09:45:11Z"
  }
}
```

#### Delete Crop

```
DELETE /crops/{id}
```

Path Parameters:

| Parameter | Type | Description |
|-----------|------|-------------|
| id | integer | Crop ID |

Example Response:

```json
{
  "status": "success",
  "data": {
    "message": "Crop deleted successfully"
  }
}
```

### Fields

#### List Fields

```
GET /fields
```

Query Parameters:

| Parameter | Type | Description |
|-----------|------|-------------|
| region | string | Filter by region name |
| crop_type | string | Filter by crop type |
| min_area | number | Minimum area in hectares |
| max_area | number | Maximum area in hectares |
| page | integer | Page number (default: 1) |
| limit | integer | Results per page (default: 20, max: 100) |

Example Response:

```json
{
  "status": "success",
  "data": [
    {
      "id": 1,
      "name": "North Cotton Field",
      "area_hectares": 120.5,
      "region": "Tashkent",
      "current_crop": "Cotton",
      "coordinates": {
        "type": "Polygon",
        "coordinates": [[[41.311, 69.240], [41.315, 69.245], [41.318, 69.242], [41.314, 69.238], [41.311, 69.240]]]
      }
    },
    ...
  ],
  "meta": {
    "pagination": {
      "total": 189,
      "pages": 10,
      "page": 1,
      "limit": 20
    }
  }
}
```

#### Get Field Details

```
GET /fields/{id}
```

Path Parameters:

| Parameter | Type | Description |
|-----------|------|-------------|
| id | integer | Field ID |

Example Response:

```json
{
  "status": "success",
  "data": {
    "id": 1,
    "name": "North Cotton Field",
    "area_hectares": 120.5,
    "region": "Tashkent",
    "current_crop": "Cotton",
    "soil_type": "Loamy",
    "irrigation_system": "Drip",
    "created_at": "2023-01-15T10:30:22Z",
    "updated_at": "2023-09-20T14:15:36Z",
    "coordinates": {
      "type": "Polygon",
      "coordinates": [[[41.311, 69.240], [41.315, 69.245], [41.318, 69.242], [41.314, 69.238], [41.311, 69.240]]]
    },
    "crop_history": [
      {
        "crop_type": "Wheat",
        "planting_date": "2022-10-10",
        "harvest_date": "2023-06-05",
        "yield_per_hectare": 4.2
      },
      {
        "crop_type": "Cotton",
        "planting_date": "2023-03-15",
        "expected_harvest_date": "2023-09-25"
      }
    ]
  }
}
```

### Analytics

#### Crop Yield Prediction

```
POST /analytics/predict/yield
```

Request Body:

```json
{
  "field_id": 1,
  "crop_type": "Cotton",
  "planting_date": "2023-03-15",
  "soil_data": {
    "type": "Loamy",
    "ph": 6.8,
    "organic_matter": 3.2
  },
  "irrigation_type": "Drip"
}
```

Required fields: `field_id`, `crop_type`, `planting_date`

Example Response:

```json
{
  "status": "success",
  "data": {
    "prediction_id": 123,
    "field_id": 1,
    "crop_type": "Cotton",
    "predicted_yield": 3.8,
    "yield_unit": "tons/hectare",
    "confidence": 0.85,
    "factors": {
      "weather": 0.4,
      "soil": 0.3,
      "historical": 0.2,
      "regional": 0.1
    },
    "harvest_window": {
      "start_date": "2023-09-15",
      "end_date": "2023-09-30",
      "optimal_date": "2023-09-22"
    }
  }
}
```

#### Disease Risk Assessment

```
POST /analytics/predict/disease
```

Request Body:

```json
{
  "field_id": 1,
  "crop_type": "Cotton",
  "current_growth_stage": "flowering",
  "weather_forecast": true
}
```

Required fields: `field_id`, `crop_type`

Example Response:

```json
{
  "status": "success",
  "data": {
    "assessment_id": 456,
    "field_id": 1,
    "crop_type": "Cotton",
    "growth_stage": "flowering",
    "diseases": [
      {
        "name": "Cotton Leaf Spot",
        "risk_level": "high",
        "risk_score": 0.78,
        "contributing_factors": [
          "Recent rainfall",
          "High humidity",
          "Historical presence in region"
        ],
        "recommended_actions": [
          "Apply fungicide within 3 days",
          "Monitor daily for symptoms",
          "Ensure proper air circulation"
        ]
      },
      {
        "name": "Cotton Boll Weevil",
        "risk_level": "medium",
        "risk_score": 0.45,
        "contributing_factors": [
          "Seasonal patterns",
          "Nearby affected fields"
        ],
        "recommended_actions": [
          "Set monitoring traps",
          "Prepare control measures"
        ]
      }
    ],
    "overall_risk": "high",
    "assessment_date": "2023-07-15T08:30:22Z"
  }
}
```

### Weather

#### Get Current Weather

```
GET /weather/current
```

Query Parameters:

| Parameter | Type | Description |
|-----------|------|-------------|
| lat | number | Latitude |
| lon | number | Longitude |
| field_id | integer | Field ID (alternative to lat/lon) |

Example Response:

```json
{
  "status": "success",
  "data": {
    "location": {
      "lat": 41.311,
      "lon": 69.240,
      "region": "Tashkent"
    },
    "current": {
      "timestamp": "2023-07-15T12:30:00Z",
      "temperature": 32.5,
      "temperature_unit": "celsius",
      "humidity": 45,
      "humidity_unit": "percent",
      "wind_speed": 12,
      "wind_speed_unit": "km/h",
      "wind_direction": 270,
      "wind_direction_unit": "degrees",
      "precipitation": 0,
      "precipitation_unit": "mm",
      "condition": "clear",
      "pressure": 1012,
      "pressure_unit": "hPa"
    }
  }
}
```

#### Get Weather Forecast

```
GET /weather/forecast
```

Query Parameters:

| Parameter | Type | Description |
|-----------|------|-------------|
| lat | number | Latitude |
| lon | number | Longitude |
| field_id | integer | Field ID (alternative to lat/lon) |
| days | integer | Number of days (default: 7, max: 14) |

Example Response:

```json
{
  "status": "success",
  "data": {
    "location": {
      "lat": 41.311,
      "lon": 69.240,
      "region": "Tashkent"
    },
    "forecast": [
      {
        "date": "2023-07-16",
        "temperature": {
          "min": 24.5,
          "max": 35.2,
          "avg": 29.8,
          "unit": "celsius"
        },
        "humidity": {
          "min": 30,
          "max": 55,
          "avg": 42,
          "unit": "percent"
        },
        "wind": {
          "speed": 10,
          "direction": 265,
          "unit": "km/h"
        },
        "precipitation": {
          "probability": 10,
          "amount": 0,
          "unit": "mm"
        },
        "condition": "clear"
      },
      ...
    ],
    "agricultural_impact": {
      "irrigation_need": "high",
      "disease_risk": "low",
      "heat_stress_risk": "medium",
      "recommendations": [
        "Increase irrigation by 20%",
        "Apply protective measures against heat stress"
      ]
    }
  }
}
```

#### Get Historical Weather

```
GET /weather/historical
```

Query Parameters:

| Parameter | Type | Description |
|-----------|------|-------------|
| lat | number | Latitude |
| lon | number | Longitude |
| field_id | integer | Field ID (alternative to lat/lon) |
| start_date | string | Start date (YYYY-MM-DD) |
| end_date | string | End date (YYYY-MM-DD) |
| interval | string | Data interval: daily, weekly, monthly (default: daily) |

Example Response:

```json
{
  "status": "success",
  "data": {
    "location": {
      "lat": 41.311,
      "lon": 69.240,
      "region": "Tashkent"
    },
    "interval": "daily",
    "historical": [
      {
        "date": "2023-06-01",
        "temperature": {
          "min": 22.5,
          "max": 33.8,
          "avg": 28.1,
          "unit": "celsius"
        },
        "humidity": {
          "avg": 48,
          "unit": "percent"
        },
        "precipitation": {
          "amount": 0,
          "unit": "mm"
        },
        "condition": "clear"
      },
      ...
    ],
    "summary": {
      "temperature": {
        "min": 20.1,
        "max": 38.5,
        "avg": 29.3,
        "unit": "celsius"
      },
      "total_precipitation": 45.2,
      "precipitation_unit": "mm",
      "avg_humidity": 52,
      "humidity_unit": "percent"
    }
  }
}
```

## Webhooks

AgroMap can send webhook notifications for various events. Configure webhooks in your account settings.

### Webhook Events

| Event | Description |
|-------|-------------|
| crop.created | A new crop has been created |
| crop.updated | A crop has been updated |
| crop.harvested | A crop has been marked as harvested |
| alert.disease | A disease risk alert has been triggered |
| alert.weather | A weather alert has been triggered |
| prediction.complete | A prediction analysis has completed |

### Webhook Payload

```json
{
  "event": "crop.created",
  "timestamp": "2023-07-15T14:30:22Z",
  "data": {
    "id": 246,
    "name": "Wheat",
    "type": "grain",
    "region": "Samarkand",
    "area_hectares": 3500
  }
}
```

### Webhook Security

Webhooks include a signature in the `X-AgroMap-Signature` header to verify the request came from AgroMap:

```
X-AgroMap-Signature: sha256=5257a869e7bdf3ecf7f52f901058cd31f3d71f3cf07e036cb110e01d1f903a3e
```

To verify the signature:
1. Get your webhook secret from your account settings
2. Create an HMAC using SHA-256 with your webhook secret as the key and the request body as the message
3. Compare the computed signature with the signature in the header

## Client Libraries

Official client libraries are available for:

- Python: [GitHub](https://github.com/agromap-uzbekistan/agromap-python)
- JavaScript: [GitHub](https://github.com/agromap-uzbekistan/agromap-js)
- PHP: [GitHub](https://github.com/agromap-uzbekistan/agromap-php)

## Support

For API support, please contact:
- Email: api-support@agromap-uzbekistan.org
- Documentation: https://docs.agromap-uzbekistan.org
- Status page: https://status.agromap-uzbekistan.org
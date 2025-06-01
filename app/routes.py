from flask import Blueprint, render_template, jsonify, request, make_response
from datetime import datetime
from app.models import CropReport, WeatherData, MapSuggestion
from app.services.weather_service import WeatherService
from app import db
import requests
import os
import logging

logger = logging.getLogger(__name__)

bp = Blueprint('main', __name__)

# Initialize weather service
weather_service = WeatherService(os.environ.get('OPENWEATHER_API_KEY', None))

@bp.route('/')
@bp.route('/index')
def index():
    return render_template('index.html', title='Home')

@bp.route('/api/crop-reports', methods=['GET', 'POST', 'PUT', 'DELETE'])
def crop_reports():
    if request.method == 'GET':
        reports = CropReport.query.filter_by(public=True).all()
        return jsonify([{
            'id': report.id,
            'crop_type': report.crop_type,
            'field_size': report.field_size,
            'latitude': report.latitude,
            'longitude': report.longitude,
            'timestamp': report.timestamp.isoformat(),
            'planting_date': report.planting_date.isoformat() if report.planting_date else None,
            'field_boundary': report.field_boundary,
            'is_owner': True  # For now, assume all reports are editable
        } for report in reports])
    
    elif request.method == 'POST':
        data = request.get_json()
        
        # Create new report
        new_report = CropReport(
            crop_type=data['crop_type'],
            field_size=float(data['field_size']),
            latitude=float(data['latitude']),
            longitude=float(data['longitude']),
            planting_date=datetime.strptime(data['planting_date'], '%Y-%m-%d').date() if data.get('planting_date') else None,
            field_boundary=data.get('field_boundary'),
            public=True
        )
        
        db.session.add(new_report)
        db.session.commit()
        
        return jsonify({'id': new_report.id}), 201
    
    elif request.method == 'PUT':
        data = request.get_json()
        report = CropReport.query.get(data['id'])
        
        if not report:
            return jsonify({'error': 'Report not found'}), 404
        
        # Update report
        report.crop_type = data['crop_type']
        report.field_size = float(data['field_size'])
        report.latitude = float(data['latitude'])
        report.longitude = float(data['longitude'])
        report.planting_date = datetime.strptime(data['planting_date'], '%Y-%m-%d').date() if data.get('planting_date') else None
        report.field_boundary = data.get('field_boundary')
        
        db.session.commit()
        return jsonify({'id': report.id})
    
    elif request.method == 'DELETE':
        report_id = request.args.get('id', type=int)
        report = CropReport.query.get(report_id)
        
        if not report:
            return jsonify({'error': 'Report not found'}), 404
        
        db.session.delete(report)
        db.session.commit()
        return jsonify({'result': 'success'})

@bp.route('/api/weather')
def get_weather():
    """Get current weather data for specified location"""
    lat = request.args.get('lat', type=float)
    lon = request.args.get('lon', type=float)
    
    if not lat or not lon:
        return jsonify({'error': 'Latitude and longitude required'}), 400
    
    weather_data = weather_service.get_weather(lat, lon)
    if not weather_data:
        return jsonify({'error': 'Weather data unavailable'}), 503
    
    return jsonify(weather_data)

@bp.route('/api/weather/forecast')
def get_weather_forecast():
    """Get weather forecast for specified location"""
    lat = request.args.get('lat', type=float)
    lon = request.args.get('lon', type=float)
    days = request.args.get('days', default=7, type=int)
    
    if not lat or not lon:
        return jsonify({'error': 'Latitude and longitude required'}), 400
    
    if days < 1 or days > 7:
        return jsonify({'error': 'Days must be between 1 and 7'}), 400
    
    forecast_data = weather_service.get_forecast(lat, lon, days)
    if not forecast_data:
        return jsonify({'error': 'Forecast data unavailable'}), 503
    
    return jsonify(forecast_data)

@bp.route('/api/weather/alerts')
def get_weather_alerts():
    """Get agricultural weather alerts for specified location"""
    lat = request.args.get('lat', type=float)
    lon = request.args.get('lon', type=float)
    
    if not lat or not lon:
        return jsonify({'error': 'Latitude and longitude required'}), 400
    
    alerts = weather_service.get_agricultural_alerts(lat, lon)
    return jsonify({'alerts': alerts})

@bp.route('/api/crop-advisor')
def crop_advisor():
    from app.services.crop_advisor import CropAdvisor
    advisor = CropAdvisor()
    
    # Get planting times for all crops
    planting_times = {}
    crops = ['wheat', 'cotton', 'potato', 'corn', 'rice']
    
    for crop in crops:
        planting_times[crop] = advisor.get_planting_time(crop) or {
            'start_month': 'Unknown', 
            'end_month': 'Unknown', 
            'is_optimal_now': False
        }
    
    return jsonify({'planting_times': planting_times})

@bp.route('/api/map-suggestions', methods=['GET', 'POST'])
def map_suggestions():
    if request.method == 'GET':
        suggestions = MapSuggestion.query.all()
        return jsonify([{
            'id': suggestion.id,
            'suggestion_type': suggestion.suggestion_type,
            'name': suggestion.name,
            'latitude': suggestion.latitude,
            'longitude': suggestion.longitude,
            'timestamp': suggestion.timestamp.isoformat()
        } for suggestion in suggestions])
    
    elif request.method == 'POST':
        data = request.get_json()
        
        new_suggestion = MapSuggestion(
            suggestion_type=data['suggestion_type'],
            name=data['name'],
            latitude=float(data['latitude']),
            longitude=float(data['longitude'])
        )
        
        db.session.add(new_suggestion)
        db.session.commit()
        
        return jsonify({'id': new_suggestion.id}), 201

@bp.route('/api/crop-trends')
def crop_trends():
    """Get aggregated crop planting trends and statistics"""
    try:
        from sqlalchemy import func
        
        # Get crop distribution by type
        crop_stats = db.session.query(
            CropReport.crop_type,
            func.count(CropReport.id).label('count'),
            func.sum(CropReport.field_size).label('total_area'),
            func.avg(CropReport.field_size).label('avg_field_size')
        ).group_by(CropReport.crop_type).all()
        
        # Get monthly planting trends
        monthly_trends = db.session.query(
            func.strftime('%Y-%m', CropReport.timestamp).label('month'),
            CropReport.crop_type,
            func.count(CropReport.id).label('count')
        ).group_by('month', CropReport.crop_type).all()
        
        # Format data
        crop_distribution = [{
            'crop_type': stat.crop_type,
            'count': stat.count,
            'total_area': float(stat.total_area),
            'avg_field_size': float(stat.avg_field_size)
        } for stat in crop_stats]
        
        trends_by_month = {}
        for trend in monthly_trends:
            month = trend.month
            if month not in trends_by_month:
                trends_by_month[month] = {}
            trends_by_month[month][trend.crop_type] = trend.count
        
        return jsonify({
            'crop_distribution': crop_distribution,
            'monthly_trends': trends_by_month
        })
    
    except Exception as e:
        return jsonify({
            'crop_distribution': [],
            'monthly_trends': {},
            'error': str(e)
        })

@bp.route('/api/price-prediction/<crop_type>')
def price_prediction(crop_type):
    """Get price prediction for a specific crop"""
    # Mock price prediction data - in a real app this would use ML models
    mock_prices = {
        'wheat': {
            'current_price': 2500,  # UZS per kg
            'predicted_price': 2650,
            'confidence': 0.75,
            'trend': 'increasing',
            'last_updated': datetime.now().isoformat()
        },
        'cotton': {
            'current_price': 8500,
            'predicted_price': 8200,
            'confidence': 0.68,
            'trend': 'decreasing',
            'last_updated': datetime.now().isoformat()
        },
        'potato': {
            'current_price': 3200,
            'predicted_price': 3400,
            'confidence': 0.72,
            'trend': 'increasing',
            'last_updated': datetime.now().isoformat()
        }
    }
    
    if crop_type in mock_prices:
        return jsonify(mock_prices[crop_type])
    else:
        return jsonify({
            'current_price': 0,
            'predicted_price': 0,
            'confidence': 0,
            'trend': 'unknown',
            'last_updated': datetime.now().isoformat(),
            'error': 'No data available for this crop'
        })

@bp.route('/api/location-from-ip')
def location_from_ip():
    """Get approximate location from IP address"""
    client_ip = request.environ.get('HTTP_X_FORWARDED_FOR') or request.environ.get('REMOTE_ADDR')
    
    # For development, return Tashkent coordinates
    if client_ip in ['127.0.0.1', 'localhost']:
        return jsonify({
            'latitude': 41.2995,
            'longitude': 69.2401,
            'city': 'Tashkent',
            'country': 'Uzbekistan'
        })
    
    try:
        # Use a free IP geolocation service
        response = requests.get(f'http://ip-api.com/json/{client_ip}', timeout=5)
        if response.status_code == 200:
            data = response.json()
            if data['status'] == 'success':
                return jsonify({
                    'latitude': data['lat'],
                    'longitude': data['lon'],
                    'city': data['city'],
                    'country': data['country']
                })
    except:
        pass
    
    # Fallback to Tashkent
    return jsonify({
        'latitude': 41.2995,
        'longitude': 69.2401,
        'city': 'Tashkent',
        'country': 'Uzbekistan'
    })

@bp.route('/set-language/<language>')
def set_language(language):
    response = make_response(jsonify({'result': 'success'}))
    response.set_cookie('language', language)
    return response

@bp.route('/api/market-analysis/<crop_type>')
def market_analysis(crop_type):
    """Get comprehensive market analysis for a specific crop"""
    try:
        from app.services.market_analyzer import MarketAnalyzer
        analyzer = MarketAnalyzer()
        
        # Get location data for regional analysis
        location_data = None
        lat = request.args.get('lat', type=float)
        lng = request.args.get('lng', type=float)
        
        if lat and lng:
            location_data = {
                'latitude': lat,
                'longitude': lng,
                'region': request.args.get('region', 'Unknown')
            }
        
        # Use enhanced market intelligence
        analysis = analyzer.get_advanced_market_intelligence(crop_type, location_data)
        return jsonify(analysis or {'error': 'Analysis not available'})
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@bp.route('/api/market-intelligence/<crop_type>')
def market_intelligence(crop_type):
    """Get detailed market intelligence and analytics"""
    try:
        from app.services.market_analyzer import MarketAnalyzer
        analyzer = MarketAnalyzer()
        
        # Get location data for regional analysis
        location_data = None
        lat = request.args.get('lat', type=float)
        lng = request.args.get('lng', type=float)
        
        if lat and lng:
            location_data = {
                'latitude': lat,
                'longitude': lng,
                'region': request.args.get('region', 'Unknown')
            }
        
        # Get comprehensive market intelligence
        intelligence = analyzer.get_advanced_market_intelligence(crop_type, location_data)
        
        if intelligence:
            # Add real-time market status
            intelligence['real_time_status'] = {
                'timestamp': datetime.now().isoformat(),
                'market_hours': 'open' if 9 <= datetime.now().hour <= 17 else 'closed',
                'last_update': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            }
            
        return jsonify(intelligence or {'error': 'Intelligence not available'})
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@bp.route('/api/harvest-price-prediction')
def harvest_price_prediction():
    """Predict price at harvest time"""
    try:
        crop_type = request.args.get('crop_type')
        planting_date = request.args.get('planting_date')
        field_size = request.args.get('field_size', type=float)
        
        if not all([crop_type, planting_date, field_size]):
            return jsonify({'error': 'Missing required parameters'}), 400
        
        from app.services.market_analyzer import MarketAnalyzer
        analyzer = MarketAnalyzer()
        
        prediction = analyzer.predict_harvest_price(crop_type, planting_date, field_size)
        return jsonify(prediction or {'error': 'Prediction not available'})
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@bp.route('/api/planting-recommendations')
def planting_recommendations():
    """Get planting recommendations based on market analysis"""
    try:
        from app.services.market_analyzer import MarketAnalyzer
        analyzer = MarketAnalyzer()
        
        recommendations = analyzer.get_planting_recommendations()
        return jsonify({'recommendations': recommendations})
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@bp.route('/api/regional-analysis')
def regional_analysis():
    """Get regional crop distribution and market analysis"""
    try:
        from sqlalchemy import func
        
        # Get crop distribution by region (simplified by lat/lng grids)
        regional_data = db.session.query(
            func.round(CropReport.latitude, 1).label('lat_region'),
            func.round(CropReport.longitude, 1).label('lng_region'),
            CropReport.crop_type,
            func.count(CropReport.id).label('farm_count'),
            func.sum(CropReport.field_size).label('total_area')
        ).filter_by(public=True)\
         .group_by('lat_region', 'lng_region', CropReport.crop_type)\
         .all()
        
        # Format data for frontend
        regions = {}
        for data in regional_data:
            region_key = f"{data.lat_region},{data.lng_region}"
            if region_key not in regions:
                regions[region_key] = {
                    'latitude': float(data.lat_region),
                    'longitude': float(data.lng_region),
                    'crops': {}
                }
            
            regions[region_key]['crops'][data.crop_type] = {
                'farm_count': data.farm_count,
                'total_area': float(data.total_area)
            }
        
        return jsonify({'regions': list(regions.values())})
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@bp.route('/api/smart-crop-recommendations')
def smart_crop_recommendations():
    """Get intelligent crop recommendations using ML-inspired algorithms"""
    try:
        from app.services.crop_advisor import CropAdvisor
        advisor = CropAdvisor()
        
        # Get location data
        lat = request.args.get('lat', type=float)
        lng = request.args.get('lng', type=float)
        region = request.args.get('region', 'Unknown')
        
        if not lat or not lng:
            return jsonify({'error': 'Latitude and longitude required'}), 400
        
        location_data = {
            'latitude': lat,
            'longitude': lng,
            'region': region
        }
        
        # Get optional parameters for enhanced recommendations
        weather_data = None
        soil_data = None
        previous_crops = None
        
        # Weather data (if provided)
        if request.args.get('temperature'):
            weather_data = {
                'temperature': request.args.get('temperature', type=float),
                'rainfall': request.args.get('rainfall', type=float, default=50),
                'humidity': request.args.get('humidity', type=float, default=60)
            }
        
        # Soil data (if provided)
        if request.args.get('soil_ph'):
            soil_data = {
                'ph': request.args.get('soil_ph', type=float),
                'organic_matter': request.args.get('organic_matter', type=float, default=2.5),
                'nitrogen': request.args.get('nitrogen', type=float, default=0.15),
                'phosphorus': request.args.get('phosphorus', type=float, default=0.08),
                'potassium': request.args.get('potassium', type=float, default=0.3)
            }
        
        # Previous crops (if provided)
        prev_crops_param = request.args.get('previous_crops')
        if prev_crops_param:
            previous_crops = prev_crops_param.split(',')
        
        # Get smart recommendations
        recommendations = advisor.get_smart_recommendations(
            location_data, weather_data, soil_data, previous_crops
        )
        
        return jsonify({
            'location': location_data,
            'recommendations': recommendations,
            'analysis_timestamp': datetime.now().isoformat(),
            'recommendation_confidence': 'high' if weather_data and soil_data else 'moderate'
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@bp.route('/api/crop-rotation-suggestions')
def crop_rotation_suggestions():
    """Get crop rotation suggestions based on previous crop"""
    try:
        from app.services.crop_advisor import CropAdvisor
        advisor = CropAdvisor()
        
        previous_crop = request.args.get('previous_crop')
        if not previous_crop:
            return jsonify({'error': 'Previous crop parameter required'}), 400
        
        suggestions = advisor.get_rotation_suggestions(previous_crop)
        
        return jsonify({
            'previous_crop': previous_crop,
            'rotation_suggestions': suggestions,
            'benefits': {
                'soil_health': 'Improved nutrient cycling',
                'pest_management': 'Natural pest and disease control',
                'yield_optimization': 'Enhanced productivity through biodiversity'
            }
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@bp.route('/api/analytics/dashboard')
def analytics_dashboard():
    """Get comprehensive analytics dashboard data"""
    try:
        from app.services.analytics_service import AnalyticsService
        analytics = AnalyticsService()
        
        # Optional filters
        start_date = request.args.get('start_date')
        end_date = request.args.get('end_date')
        region = request.args.get('region')
          dashboard_data = analytics.get_comprehensive_dashboard_data()
        
        return jsonify(dashboard_data)
        
    except Exception as e:
        logger.error(f"Error generating analytics dashboard: {e}")
        return jsonify({'error': str(e)}), 500

@bp.route('/api/analytics/export')
def analytics_export():
    """Export analytics data in specified format"""
    try:
        from app.services.analytics_service import AnalyticsService
        analytics = AnalyticsService()
        
        format_type = request.args.get('format', 'json')
        include_raw = request.args.get('include_raw', 'false').lower() == 'true'
        
        if format_type not in ['json', 'csv']:
            return jsonify({'error': 'Supported formats: json, csv'}), 400
        
        export_data = analytics.export_analytics_data(
            format_type=format_type,
            include_raw_data=include_raw
        )
        
        if format_type == 'csv':
            response = make_response(export_data)
            response.headers['Content-Type'] = 'text/csv'
            response.headers['Content-Disposition'] = f'attachment; filename=agromap_analytics_{datetime.now().strftime("%Y%m%d")}.csv'
            return response
        else:
            return jsonify({'data': export_data})
        
    except Exception as e:
        logger.error(f"Error exporting analytics data: {e}")
        return jsonify({'error': str(e)}), 500

@bp.route('/api/crop-rotation/plan')
def generate_rotation_plan():
    """Generate optimized crop rotation plan"""
    try:
        from app.services.crop_rotation_planner import CropRotationPlanner
        planner = CropRotationPlanner()
        
        # Required parameters
        lat = request.args.get('lat', type=float)
        lng = request.args.get('lng', type=float)
        field_size = request.args.get('field_size', type=float, default=1.0)
        
        if not lat or not lng:
            return jsonify({'error': 'Latitude and longitude required'}), 400
        
        # Optional parameters
        years = request.args.get('years', type=int, default=3)
        preferred_crops = request.args.get('preferred_crops', '').split(',') if request.args.get('preferred_crops') else None
        avoid_crops = request.args.get('avoid_crops', '').split(',') if request.args.get('avoid_crops') else None
        
        # Clean up crop lists (remove empty strings)
        if preferred_crops:
            preferred_crops = [crop.strip() for crop in preferred_crops if crop.strip()]
        if avoid_crops:
            avoid_crops = [crop.strip() for crop in avoid_crops if crop.strip()]
        
        # Generate rotation plan
        rotation_plan = planner.generate_rotation_plan(
            field_location=(lat, lng),
            field_size=field_size,
            years=years,
            preferred_crops=preferred_crops,
            avoid_crops=avoid_crops
        )
        
        # Convert to JSON-serializable format
        plan_data = {
            'field_id': rotation_plan.field_id,
            'field_location': {'latitude': lat, 'longitude': lng},
            'field_size': field_size,
            'years_planned': years,
            'seasons': rotation_plan.seasons,
            'scores': {
                'sustainability': rotation_plan.sustainability_score,
                'economic': rotation_plan.economic_score,
                'risk': rotation_plan.risk_score
            },
            'recommendations': rotation_plan.recommendations,
            'generated_at': datetime.now().isoformat()
        }
        
        return jsonify(plan_data)
        
    except Exception as e:
        logger.error(f"Error generating rotation plan: {e}")
        return jsonify({'error': str(e)}), 500

@bp.route('/api/crop-rotation/export')
def export_rotation_plan():
    """Export rotation plan in specified format"""
    try:
        from app.services.crop_rotation_planner import CropRotationPlanner
        planner = CropRotationPlanner()
        
        # First generate the plan
        lat = request.args.get('lat', type=float)
        lng = request.args.get('lng', type=float)
        field_size = request.args.get('field_size', type=float, default=1.0)
        years = request.args.get('years', type=int, default=3)
        format_type = request.args.get('format', 'json')
        
        if not lat or not lng:
            return jsonify({'error': 'Latitude and longitude required'}), 400
        
        if format_type not in ['json', 'csv']:
            return jsonify({'error': 'Supported formats: json, csv'}), 400
        
        # Generate rotation plan
        rotation_plan = planner.generate_rotation_plan(
            field_location=(lat, lng),
            field_size=field_size,
            years=years
        )
        
        # Export in requested format
        export_data = planner.export_rotation_plan(rotation_plan, format_type)
        
        if format_type == 'csv':
            response = make_response(export_data)
            response.headers['Content-Type'] = 'text/csv'
            response.headers['Content-Disposition'] = f'attachment; filename=rotation_plan_{rotation_plan.field_id}.csv'
            return response
        else:
            return jsonify({'data': export_data})
        
    except Exception as e:
        logger.error(f"Error exporting rotation plan: {e}")
        return jsonify({'error': str(e)}), 500

@bp.route('/api/analytics/crop-diversity')
def get_crop_diversity_analysis():
    """Get detailed crop diversity analysis"""
    try:
        from app.services.analytics_service import AnalyticsService
        analytics = AnalyticsService()
        
        region = request.args.get('region')
        
        diversity_data = analytics.get_crop_diversity_metrics(region_filter=region)
        
        return jsonify({
            'diversity_analysis': diversity_data,
            'generated_at': datetime.now().isoformat(),
            'region': region or 'all_regions'
        })
        
    except Exception as e:
        logger.error(f"Error getting crop diversity analysis: {e}")
        return jsonify({'error': str(e)}), 500

@bp.route('/api/analytics/temporal-trends')
def get_temporal_trends():
    """Get temporal trends analysis"""
    try:
        from app.services.analytics_service import AnalyticsService
        analytics = AnalyticsService()
        
        months = request.args.get('months', type=int, default=12)
        crop_type = request.args.get('crop_type')
        
        trends_data = analytics.get_temporal_trends(
            months_back=months,
            crop_filter=crop_type
        )
        
        return jsonify({
            'temporal_trends': trends_data,
            'analysis_period_months': months,
            'crop_filter': crop_type,
            'generated_at': datetime.now().isoformat()
        })
        
    except Exception as e:
        logger.error(f"Error getting temporal trends: {e}")
        return jsonify({'error': str(e)}), 500

@bp.route('/api/crop-rotation/available-crops')
def get_available_crops():
    """Get list of available crops for rotation planning"""
    try:
        from app.services.crop_rotation_planner import CropRotationPlanner
        planner = CropRotationPlanner()
        
        # Get crop compatibility information
        crops_info = []
        for crop_type, compatibility in planner.crop_compatibility.items():
            crops_info.append({
                'crop_type': crop_type,
                'nitrogen_requirement': compatibility.nitrogen_requirement,
                'nitrogen_production': compatibility.nitrogen_production,
                'water_requirement': compatibility.water_requirement,
                'growth_period_days': compatibility.growth_period,
                'optimal_seasons': [season.value for season in compatibility.optimal_seasons],
                'soil_improvement': compatibility.soil_improvement,
                'pest_resistance': compatibility.pest_resistance,
                'disease_resistance': compatibility.disease_resistance
            })
        
        return jsonify({
            'available_crops': crops_info,
            'total_crops': len(crops_info)
        })
        
    except Exception as e:
        logger.error(f"Error getting available crops: {e}")
        return jsonify({'error': str(e)}), 500
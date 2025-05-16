from flask import Blueprint, render_template, jsonify, request, make_response
from datetime import datetime

bp = Blueprint('main', __name__)

# Mock data for demonstration
MOCK_CROP_REPORTS = [
    {
        'id': 1,
        'crop_type': 'wheat',
        'field_size': 5.2,
        'latitude': 41.3111,
        'longitude': 69.2797,
        'timestamp': datetime.now().isoformat(),
        'planting_date': '2023-10-15',
        'field_boundary': None,
        'is_owner': True
    },
    {
        'id': 2,
        'crop_type': 'cotton',
        'field_size': 3.7,
        'latitude': 41.2995,
        'longitude': 69.2401,
        'timestamp': datetime.now().isoformat(),
        'planting_date': '2023-04-20',
        'field_boundary': None,
        'is_owner': False
    },
    {
        'id': 3,
        'crop_type': 'potato',
        'field_size': 2.1,
        'latitude': 41.3419,
        'longitude': 69.3044,
        'timestamp': datetime.now().isoformat(),
        'planting_date': '2023-03-10',
        'field_boundary': None,
        'is_owner': True
    }
]

@bp.route('/')
@bp.route('/index')
def index():
    return render_template('index.html', title='Home')

@bp.route('/api/crop-reports', methods=['GET', 'POST', 'PUT', 'DELETE'])
def crop_reports():
    if request.method == 'GET':
        return jsonify(MOCK_CROP_REPORTS)
    
    elif request.method == 'POST':
        # Mock adding a new report (in a real app this would save to database)
        data = request.get_json()
        new_report = {
            'id': len(MOCK_CROP_REPORTS) + 1,
            'crop_type': data['crop_type'],
            'field_size': data['field_size'],
            'latitude': data['latitude'],
            'longitude': data['longitude'],
            'timestamp': datetime.now().isoformat(),
            'planting_date': data.get('planting_date'),
            'field_boundary': data.get('field_boundary'),
            'is_owner': True
        }
        MOCK_CROP_REPORTS.append(new_report)
        return jsonify({'id': new_report['id']}), 201
    
    elif request.method == 'PUT':
        data = request.get_json()
        for report in MOCK_CROP_REPORTS:
            if report['id'] == data['id']:
                report['crop_type'] = data['crop_type']
                report['field_size'] = data['field_size']
                report['latitude'] = data['latitude']
                report['longitude'] = data['longitude']
                report['planting_date'] = data.get('planting_date')
                report['field_boundary'] = data.get('field_boundary')
                return jsonify({'id': report['id']})
        return jsonify({'error': 'Report not found'}), 404
    
    elif request.method == 'DELETE':
        report_id = request.args.get('id', type=int)
        for i, report in enumerate(MOCK_CROP_REPORTS):
            if report['id'] == report_id:
                del MOCK_CROP_REPORTS[i]
                return jsonify({'result': 'success'})
        return jsonify({'error': 'Report not found'}), 404

@bp.route('/api/weather')
def get_weather():
    # Return mock weather data
    weather = {
        'temperature': 25,
        'humidity': 45,
        'wind_speed': 5,
        'precipitation': 0,
        'location': 'Tashkent'
    }
    return jsonify(weather)

@bp.route('/api/crop-advisor')
def crop_advisor():
    # Return mock advisory data
    planting_times = {
        'wheat': {'start_month': 'October', 'end_month': 'November', 'is_optimal_now': True},
        'cotton': {'start_month': 'April', 'end_month': 'May', 'is_optimal_now': False},
        'potato': {'start_month': 'March', 'end_month': 'April', 'is_optimal_now': False},
        'corn': {'start_month': 'April', 'end_month': 'May', 'is_optimal_now': False},
        'rice': {'start_month': 'May', 'end_month': 'June', 'is_optimal_now': False}
    }
    return jsonify({'planting_times': planting_times})

@bp.route('/set-language/<language>')
def set_language(language):
    response = make_response(jsonify({'result': 'success'}))
    response.set_cookie('language', language)
    return response
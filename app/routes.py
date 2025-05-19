from flask import render_template, redirect, url_for, flash, request, jsonify
from flask_login import login_user, logout_user, current_user, login_required
from app import app, db
from app.models import User, Crop, Field, WeatherData, Report
import folium
from datetime import datetime
import json

@app.route('/')
def index():
    return render_template('index.html', title='AgroMap Uzbekistan')

@app.route('/dashboard')
@login_required
def dashboard():
    return render_template('dashboard.html', title='Dashboard')

@app.route('/map')
def map():
    # Create a map centered on Uzbekistan
    m = folium.Map(location=[41.3775, 64.5853], zoom_start=6)
    folium_map = m._repr_html_()
    return render_template('map.html', title='Interactive Map', map=folium_map)

@app.route('/crops')
@login_required
def crops():
    all_crops = Crop.query.all()
    return render_template('crops.html', title='Crop Management', crops=all_crops)

@app.route('/fields')
@login_required
def fields():
    user_fields = Field.query.filter_by(user_id=current_user.id).all()
    return render_template('fields.html', title='Field Management', fields=user_fields)

@app.route('/weather')
def weather():
    current_weather = WeatherData.query.order_by(WeatherData.timestamp.desc()).first()
    return render_template('weather.html', title='Weather Information', weather=current_weather)

@app.route('/reports')
@login_required
def reports():
    user_reports = Report.query.filter_by(user_id=current_user.id).all()
    return render_template('reports.html', title='Reports', reports=user_reports)

@app.route('/analytics')
@login_required
def analytics():
    return render_template('analytics.html', title='Analytics')

@app.route('/profile')
@login_required
def profile():
    return render_template('profile.html', title='User Profile')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('index'))
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        user = User.query.filter_by(email=email).first()
        if user and user.check_password(password):
            login_user(user)
            next_page = request.args.get('next')
            return redirect(next_page or url_for('index'))
        else:
            flash('Invalid email or password')
    return render_template('login.html', title='Login')

@app.route('/logout')
def logout():
    logout_user()
    return redirect(url_for('index'))

@app.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('index'))
    if request.method == 'POST':
        email = request.form.get('email')
        username = request.form.get('username')
        password = request.form.get('password')
        
        if User.query.filter_by(email=email).first():
            flash('Email already registered')
            return redirect(url_for('register'))
            
        user = User(email=email, username=username)
        user.set_password(password)
        db.session.add(user)
        db.session.commit()
        
        flash('Registration successful! Please login.')
        return redirect(url_for('login'))
    return render_template('register.html', title='Register')

@app.route('/api/fields', methods=['GET', 'POST'])
@login_required
def api_fields():
    if request.method == 'POST':
        data = request.get_json()
        
        # Convert string dates to datetime objects if provided
        planting_date = None
        if data.get('planting_date'):
            try:
                planting_date = datetime.strptime(data.get('planting_date'), '%Y-%m-%d')
            except ValueError:
                return jsonify({'error': 'Invalid planting date format. Use YYYY-MM-DD.'}), 400
        
        harvest_date = None
        if data.get('harvest_date'):
            try:
                harvest_date = datetime.strptime(data.get('harvest_date'), '%Y-%m-%d')
            except ValueError:
                return jsonify({'error': 'Invalid harvest date format. Use YYYY-MM-DD.'}), 400
        
        # Create new field
        new_field = Field(
            name=data.get('name'),
            location=data.get('location'),
            area=data.get('area'),
            geometry=json.dumps(data.get('geometry')) if data.get('geometry') else None,
            user_id=current_user.id,
            crop_id=data.get('crop_id'),
            planting_date=planting_date,
            harvest_date=harvest_date
        )
        db.session.add(new_field)
        db.session.commit()
        return jsonify(new_field.to_dict()), 201
    
    fields = Field.query.filter_by(user_id=current_user.id).all()
    return jsonify([field.to_dict() for field in fields])

@app.route('/api/fields/<int:field_id>', methods=['GET', 'PUT', 'DELETE'])
@login_required
def api_field_detail(field_id):
    field = Field.query.get_or_404(field_id)
    
    # Ensure the user owns this field
    if field.user_id != current_user.id:
        return jsonify({'error': 'Unauthorized access'}), 403
    
    if request.method == 'GET':
        return jsonify(field.to_dict())
    
    elif request.method == 'PUT':
        data = request.get_json()
        
        # Handle date conversions
        if data.get('planting_date'):
            try:
                field.planting_date = datetime.strptime(data.get('planting_date'), '%Y-%m-%d')
            except ValueError:
                return jsonify({'error': 'Invalid planting date format. Use YYYY-MM-DD.'}), 400
        else:
            field.planting_date = None
        
        if data.get('harvest_date'):
            try:
                field.harvest_date = datetime.strptime(data.get('harvest_date'), '%Y-%m-%d')
            except ValueError:
                return jsonify({'error': 'Invalid harvest date format. Use YYYY-MM-DD.'}), 400
        else:
            field.harvest_date = None
        
        # Update other fields
        field.name = data.get('name', field.name)
        field.location = data.get('location', field.location)
        field.area = data.get('area', field.area)
        if data.get('geometry'):
            field.geometry = json.dumps(data.get('geometry'))
        field.crop_id = data.get('crop_id', field.crop_id)
        
        db.session.commit()
        return jsonify(field.to_dict())
    
    elif request.method == 'DELETE':
        db.session.delete(field)
        db.session.commit()
        return jsonify({'message': 'Field deleted successfully'}), 200

@app.route('/api/crops', methods=['GET', 'POST'])
@login_required
def api_crops():
    if request.method == 'POST':
        data = request.get_json()
        new_crop = Crop(
            name=data.get('name'),
            description=data.get('description'),
            growing_season=data.get('growing_season'),
            water_requirements=data.get('water_requirements')
        )
        db.session.add(new_crop)
        db.session.commit()
        return jsonify(new_crop.to_dict()), 201
    
    crops = Crop.query.all()
    return jsonify([crop.to_dict() for crop in crops])

@app.route('/api/weather', methods=['GET'])
def api_weather():
    weather = WeatherData.query.order_by(WeatherData.timestamp.desc()).limit(10).all()
    return jsonify([w.to_dict() for w in weather])

@app.route('/api/weather/<location>', methods=['GET'])
def api_weather_by_location(location):
    # Get the most recent weather data for the specified location
    weather = WeatherData.query.filter_by(location=location).order_by(WeatherData.timestamp.desc()).first()
    
    if not weather:
        return jsonify({'error': 'Weather data not found for this location'}), 404
    
    return jsonify(weather.to_dict())

@app.route('/api/reports', methods=['GET', 'POST'])
@login_required
def api_reports():
    if request.method == 'POST':
        data = request.get_json()
        new_report = Report(
            title=data.get('title'),
            content=data.get('content'),
            location=data.get('location'),
            user_id=current_user.id,
            timestamp=datetime.now()
        )
        db.session.add(new_report)
        db.session.commit()
        return jsonify(new_report.to_dict()), 201
    
    reports = Report.query.filter_by(user_id=current_user.id).all()
    return jsonify([report.to_dict() for report in reports])

@app.route('/api/reports/<int:report_id>', methods=['GET', 'PUT', 'DELETE'])
@login_required
def api_report_detail(report_id):
    report = Report.query.get_or_404(report_id)
    
    # Ensure the user owns this report
    if report.user_id != current_user.id:
        return jsonify({'error': 'Unauthorized access'}), 403
    
    if request.method == 'GET':
        return jsonify(report.to_dict())
    
    elif request.method == 'PUT':
        data = request.get_json()
        report.title = data.get('title', report.title)
        report.content = data.get('content', report.content)
        report.location = data.get('location', report.location)
        db.session.commit()
        return jsonify(report.to_dict())
    
    elif request.method == 'DELETE':
        db.session.delete(report)
        db.session.commit()
        return jsonify({'message': 'Report deleted successfully'}), 200

@app.route('/api/crops/<int:crop_id>', methods=['GET', 'PUT', 'DELETE'])
@login_required
def api_crop_detail(crop_id):
    crop = Crop.query.get_or_404(crop_id)
    
    if request.method == 'GET':
        return jsonify(crop.to_dict())
    
    elif request.method == 'PUT':
        data = request.get_json()
        crop.name = data.get('name', crop.name)
        crop.description = data.get('description', crop.description)
        crop.growing_season = data.get('growing_season', crop.growing_season)
        crop.water_requirements = data.get('water_requirements', crop.water_requirements)
        db.session.commit()
        return jsonify(crop.to_dict())
    
    elif request.method == 'DELETE':
        # Check if crop is being used in any fields
        fields_with_crop = Field.query.filter_by(crop_id=crop_id).all()
        if fields_with_crop:
            # Option 1: Return error
            # return jsonify({'error': 'Cannot delete crop that is in use by fields'}), 400
            
            # Option 2: Remove crop from fields and then delete crop
            for field in fields_with_crop:
                field.crop_id = None
        
        db.session.delete(crop)
        db.session.commit()
        return jsonify({'message': 'Crop deleted successfully'}), 200

@app.route('/api/crops/<int:crop_id>/statistics', methods=['GET'])
@login_required
def api_crop_statistics(crop_id):
    crop = Crop.query.get_or_404(crop_id)
    
    # Get all fields using this crop
    fields = Field.query.filter_by(crop_id=crop_id).all()
    
    # Calculate statistics
    total_fields = len(fields)
    total_area = sum(field.area for field in fields) if fields else 0
    
    return jsonify({
        'crop_id': crop_id,
        'crop_name': crop.name,
        'total_fields': total_fields,
        'total_area': total_area
    })

@app.route('/api/profile', methods=['GET', 'PUT'])
@login_required
def api_profile():
    if request.method == 'GET':
        return jsonify(current_user.to_dict())
    
    elif request.method == 'PUT':
        data = request.get_json()
        
        # Update username if provided and not already taken
        if data.get('username') and data.get('username') != current_user.username:
            if User.query.filter_by(username=data.get('username')).first():
                return jsonify({'error': 'Username already taken'}), 400
            current_user.username = data.get('username')
        
        # Update email if provided and not already taken
        if data.get('email') and data.get('email') != current_user.email:
            if User.query.filter_by(email=data.get('email')).first():
                return jsonify({'error': 'Email already registered'}), 400
            current_user.email = data.get('email')
        
        # Update password if provided
        if data.get('password'):
            current_user.set_password(data.get('password'))
        
        db.session.commit()
        return jsonify(current_user.to_dict())

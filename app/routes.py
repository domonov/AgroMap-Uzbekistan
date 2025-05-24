from flask import render_template, redirect, url_for, flash, request, jsonify
from flask_login import login_user, logout_user, current_user, login_required
from app import app, db
from app.models import User, Crop, Field, WeatherData, Report
from datetime import datetime
import json
from flask_babel import gettext as _ # Added import

@app.route('/')
def index():
    return render_template('index.html', title=_('AgroMap Uzbekistan')) # Marked

@app.route('/dashboard')
@login_required
def dashboard():
    return render_template('dashboard.html', title=_('Dashboard')) # Marked

@app.route('/map')
def map():
    return render_template('map.html', title=_('Interactive Map')) # Marked

@app.route('/crops')
@login_required
def crops():
    all_crops = Crop.query.all()
    return render_template('crops.html', title=_('Crop Management'), crops=all_crops) # Marked

@app.route('/fields')
@login_required
def fields():
    user_fields = Field.query.filter_by(user_id=current_user.id).all()
    return render_template('fields.html', title=_('Field Management'), fields=user_fields) # Marked

@app.route('/weather')
def weather():
    location = request.args.get('location')
    current_weather = None # Initialize current_weather
    if location:
        current_weather = WeatherData.query.filter_by(location=location).order_by(WeatherData.timestamp.desc()).first() # Added logic
    else:
        # Default to a general location or the first available if no specific location is provided
        current_weather = WeatherData.query.order_by(WeatherData.timestamp.desc()).first() # Added logic
    
    # Process forecast data if present
    if current_weather and current_weather.forecast:
        current_weather.forecast_data = json.loads(current_weather.forecast) # Added logic
    
    return render_template('weather.html', title=_('Weather Information'), weather=current_weather) # Marked

@app.route('/reports')
@login_required
def reports():
    user_reports = Report.query.filter_by(user_id=current_user.id).all()
    return render_template('reports.html', title=_('Reports'), reports=user_reports) # Marked

@app.route('/analytics')
@login_required
def analytics():
    return render_template('analytics.html', title=_('Analytics')) # Marked

@app.route('/profile')
@login_required
def profile():
    return render_template('profile.html', title=_('User Profile')) # Marked

@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('index'))
    if request.method == 'POST':
        email_or_username = request.form.get('email') # Changed from 'username' to 'email' to match form
        password = request.form.get('password')
        print(f"[LOGIN DEBUG] Attempting login for email/username: '{email_or_username}' with password: '{password}'")
        
        # Try to find user by email first, then by username if you want to support both
        user = User.query.filter_by(email=email_or_username).first()
        if not user: # If not found by email, try by username
            user = User.query.filter_by(username=email_or_username).first()
            if user:
                print(f"[LOGIN DEBUG] User '{email_or_username}' found by username in database. ID: {user.id}, Email: {user.email}, Role: {user.role}")

        if user:
            if user.email == email_or_username: # Log if found by email
                 print(f"[LOGIN DEBUG] User with email '{email_or_username}' found in database. ID: {user.id}, Username: {user.username}, Role: {user.role}")
            password_check_result = user.check_password(password)
            print(f"[LOGIN DEBUG] Password check for user '{user.username}': {password_check_result}")
            if not password_check_result:
                flash(_('Invalid email/username or password')) # Updated message
                print("[LOGIN DEBUG] Password check failed.")
                return redirect(url_for('login'))
        else:
            flash(_('Invalid email/username or password')) # Updated message
            print(f"[LOGIN DEBUG] User with email/username '{email_or_username}' not found in database.")
            return redirect(url_for('login'))
        
        login_user(user, remember=request.form.get('remember_me'))
        print(f"[LOGIN DEBUG] Login successful for user '{user.username}'. Redirecting to dashboard.")
        return redirect(url_for('dashboard'))
    return render_template('login.html', title=_('Login')) # Marked

@app.route('/logout')
def logout():
    logout_user()
    return redirect(url_for('index'))

@app.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('index'))
    if request.method == 'POST':
        username = request.form.get('username')
        email = request.form.get('email')
        password = request.form.get('password')
        # Add validation for username, email, password here (e.g., check if user already exists)
        user = User(username=username, email=email)
        user.set_password(password)
        db.session.add(user)
        db.session.commit()
        flash(_('Congratulations, you are now a registered user!')) # Marked
        return redirect(url_for('login'))
    return render_template('register.html', title=_('Register')) # Marked


@app.route('/api/fields', methods=['GET', 'POST'])
@login_required
def api_fields():
    if request.method == 'POST': # Added logic for POST
        data = request.get_json() or {}
        # Add validation for data here
        field = Field(
            name=data.get('name'),
            location=data.get('location'),
            area=data.get('area'),
            geometry=json.dumps(data.get('geometry')),
            user_id=current_user.id,
            crop_id=data.get('crop_id'),
            planting_date=datetime.strptime(data.get('planting_date'), '%Y-%m-%d') if data.get('planting_date') else None,
            harvest_date=datetime.strptime(data.get('harvest_date'), '%Y-%m-%d') if data.get('harvest_date') else None
        )
        db.session.add(field)
        db.session.commit()
        return jsonify(field.to_dict()), 201
    fields = Field.query.filter_by(user_id=current_user.id).all() # Added logic for GET
    return jsonify([field.to_dict() for field in fields])

@app.route('/api/fields/<int:field_id>', methods=['GET', 'PUT', 'DELETE'])
@login_required
def api_field_detail(field_id):
    field = Field.query.get_or_404(field_id)
    if field.user_id != current_user.id: # Check ownership
        return jsonify({'error': 'Forbidden'}), 403
    if request.method == 'GET': # Added logic for GET
        return jsonify(field.to_dict())
    elif request.method == 'PUT': # Added logic for PUT
        data = request.get_json() or {}
        # Update fields as needed, e.g.:
        field.name = data.get('name', field.name)
        field.location = data.get('location', field.location)
        # ... other fields
        db.session.commit()
        return jsonify(field.to_dict())
    elif request.method == 'DELETE': # Added logic for DELETE
        db.session.delete(field)
        db.session.commit()
        return jsonify({'message': 'Field deleted'})
    return jsonify({'error': 'Method not allowed'}), 405 # Fallback

@app.route('/api/crops', methods=['GET', 'POST'])
@login_required # Should be restricted to admin or specific roles if POST is for creation
def api_crops():
    if request.method == 'POST': # Added logic for POST (assuming admin functionality)
        data = request.get_json() or {}
        # Add validation for data here
        crop = Crop(
            name=data.get('name'),
            description=data.get('description'),
            growing_season=data.get('growing_season'),
            water_requirements=data.get('water_requirements')
        )
        db.session.add(crop)
        db.session.commit()
        return jsonify(crop.to_dict()), 201
    crops = Crop.query.all() # Added logic for GET
    return jsonify([crop.to_dict() for crop in crops])

@app.route('/api/weather', methods=['GET'])
def api_weather():
    # Example: Get latest weather for all locations or a default one
    weather_data = WeatherData.query.order_by(WeatherData.timestamp.desc()).limit(5).all() # Added logic
    return jsonify([data.to_dict() for data in weather_data])

@app.route('/api/weather/<location>', methods=['GET'])
def api_weather_by_location(location):
    weather_data = WeatherData.query.filter_by(location=location).order_by(WeatherData.timestamp.desc()).first() # Added logic
    if weather_data:
        return jsonify(weather_data.to_dict())
    return jsonify({'error': 'Weather data not found for this location'}), 404

@app.route('/api/reports', methods=['GET', 'POST'])
@login_required
def api_reports():
    if request.method == 'POST': # Added logic for POST
        data = request.get_json() or {}
        report = Report(
            title=data.get('title'),
            content=data.get('content'),
            location=data.get('location'),
            user_id=current_user.id
        )
        db.session.add(report)
        db.session.commit()
        return jsonify(report.to_dict()), 201
    reports = Report.query.filter_by(user_id=current_user.id).all() # Added logic for GET
    return jsonify([report.to_dict() for report in reports])

@app.route('/api/reports/<int:report_id>', methods=['GET', 'PUT', 'DELETE'])
@login_required
def api_report_detail(report_id):
    report = Report.query.get_or_404(report_id)
    if report.user_id != current_user.id: # Check ownership
        return jsonify({'error': 'Forbidden'}), 403
    if request.method == 'GET': # Added logic for GET
        return jsonify(report.to_dict())
    elif request.method == 'PUT': # Added logic for PUT
        data = request.get_json() or {}
        report.title = data.get('title', report.title)
        report.content = data.get('content', report.content)
        report.location = data.get('location', report.location)
        db.session.commit()
        return jsonify(report.to_dict())
    elif request.method == 'DELETE': # Added logic for DELETE
        db.session.delete(report)
        db.session.commit()
        return jsonify({'message': 'Report deleted'})
    return jsonify({'error': 'Method not allowed'}), 405 # Fallback

@app.route('/api/crops/<int:crop_id>', methods=['GET', 'PUT', 'DELETE'])
@login_required # Should be restricted to admin or specific roles for PUT/DELETE
def api_crop_detail(crop_id):
    crop = Crop.query.get_or_404(crop_id)
    if request.method == 'GET': # Added logic for GET
        return jsonify(crop.to_dict())
    # Add role check for PUT/DELETE if not all logged-in users can modify crops
    # if current_user.role != 'admin':
    #     return jsonify({'error': 'Forbidden'}), 403
    elif request.method == 'PUT': # Added logic for PUT
        data = request.get_json() or {}
        crop.name = data.get('name', crop.name)
        crop.description = data.get('description', crop.description)
        # ... other fields
        db.session.commit()
        return jsonify(crop.to_dict())
    elif request.method == 'DELETE': # Added logic for DELETE
        db.session.delete(crop)
        db.session.commit()
        return jsonify({'message': 'Crop deleted'})
    return jsonify({'error': 'Method not allowed'}), 405 # Fallback

@app.route('/api/crops/<int:crop_id>/statistics', methods=['GET'])
@login_required
def api_crop_statistics(crop_id):
    # Example: Fetch statistics related to a crop
    # This is a placeholder, actual implementation will depend on data model and requirements
    crop = Crop.query.get_or_404(crop_id)
    # Dummy statistics
    stats = {
        'crop_name': crop.name,
        'total_fields': Field.query.filter_by(crop_id=crop_id).count(),
        'average_area': db.session.query(db.func.avg(Field.area)).filter(Field.crop_id == crop_id).scalar() or 0
    }
    return jsonify(stats)

@app.route('/api/profile', methods=['GET', 'PUT'])
@login_required
def api_profile():
    user = current_user
    if request.method == 'PUT': # Added logic for PUT
        data = request.get_json() or {}
        # Update user profile, e.g., email. Username change might need more consideration.
        user.email = data.get('email', user.email)
        # Password change should be handled separately with current password verification
        db.session.commit()
        return jsonify(user.to_dict())
    return jsonify(user.to_dict()) # Added logic for GET

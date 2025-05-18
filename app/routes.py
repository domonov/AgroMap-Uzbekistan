"""Route handlers for AgroMap."""
from datetime import datetime, timedelta, timedelta
from functools import wraps
import secrets
import requests
from flask import (
    Blueprint, render_template, request, flash, redirect, 
    url_for, jsonify, session, send_file
)
from app.models import db, User, CropReport, Field, Weather, Prediction
from werkzeug.security import generate_password_hash, check_password_hash
from flask_login import login_user, logout_user, login_required, current_user

auth_bp = Blueprint('auth', __name__)
main_bp = Blueprint('main', __name__)

@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    """Handle user login."""
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        user = User.query.filter_by(email=email).first()

        if user and check_password_hash(user.password_hash, password):
            login_user(user)
            session['user_id'] = user.id
            flash('Login successful!', 'success')
            return redirect(url_for('main.dashboard'))
        
        flash('Invalid email or password', 'error')
    return render_template('login.html')

@auth_bp.route('/logout')
@login_required
def logout():
    """Handle user logout."""
    logout_user()
    session.pop('user_id', None)
    flash('You have been logged out.', 'info')
    return redirect(url_for('main.index'))

@auth_bp.route('/register', methods=['GET', 'POST'])
def register():
    """Handle user registration."""
    if request.method == 'POST':
        email = request.form.get('email')
        username = request.form.get('username')
        password = request.form.get('password')

        if User.query.filter_by(email=email).first():
            flash('Email already registered', 'error')
            return render_template('register.html')

        user = User(
            email=email,
            username=username,
            password_hash=generate_password_hash(password)
        )
        db.session.add(user)
        db.session.commit()

        flash('Registration successful!', 'success')
        return redirect(url_for('auth.login'))
    
    return render_template('register.html')

@auth_bp.route('/reset-password', methods=['GET', 'POST'])
def reset_password():
    """Handle password reset requests."""
    if request.method == 'POST':
        email = request.form.get('email')
        user = User.query.filter_by(email=email).first()
        
        if user:
            token = secrets.token_urlsafe(16)
            user.reset_token = token
            user.reset_token_expires = datetime.utcnow() + timedelta(hours=1)
            db.session.commit()
            
            # Send reset email (implement email sending)
            flash('Password reset instructions sent to your email.', 'info')
            return redirect(url_for('auth.login'))
        
        flash('Email not found.', 'error')
    return render_template('request_reset.html')

@main_bp.route('/')
def index():
    """Home page."""
    return render_template('index.html')

@main_bp.route('/dashboard')
@login_required
def dashboard():
    """User dashboard."""
    return render_template('dashboard.html')

@main_bp.route('/profile')
@login_required
def profile():
    """User profile page."""
    return render_template('profile.html')

@main_bp.route('/offline')
def offline():
    """Offline page."""
    return render_template('offline.html')

@main_bp.route('/service-worker.js')
def service_worker():
    """Service worker for offline functionality."""
    return send_file('static/js/service-worker.js', mimetype='application/javascript')

@main_bp.route('/manifest.json')
def manifest():
    """Web app manifest."""
    return send_file('static/manifest.json', mimetype='application/json')

def init_app(app):
    """Initialize routes with the app."""
    app.register_blueprint(auth_bp, url_prefix='/auth')
    app.register_blueprint(main_bp)

# 📌 Route: Home Page (Displays Map)
@main_bp.route("/")
def home():
    return render_template("index.html")  # Renders main map page

# 📌 Route: Get User Location
@main_bp.route("/get-location")
def get_location():
    ip = request.remote_addr  # Get user's IP (not always accurate)
    location_data = requests.get(f"https://ipinfo.io/{ip}/json").json()
    return jsonify(location_data)  # Returns general location data

# 📌 Validation utilities
from app.utils import validate_crop_data

# Update crop report submission to use validation
@main_bp.route("/submit", methods=["POST"])
def submit_crop():
    if request.content_type.startswith('application/json'):
        data = request.json
    else:
        data = request.form
    if not validate_crop_data(data):
        return jsonify({"error": "Missing or invalid required fields."}), 400
    crop_type = data.get("crop_type")
    latitude = data.get("latitude")
    longitude = data.get("longitude")
    area_size = data.get("area_size")
    try:
        report = CropReport(
            crop_type=crop_type,
            latitude=float(latitude),
            longitude=float(longitude),
            area_size=float(area_size)
        )
        db.session.add(report)
        db.session.commit()
        return jsonify({"message": "Crop report added!"}), 201
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# 📌 Route: Get Reports for Heatmap
@main_bp.route("/reports", methods=["GET"])
def get_reports():
    reports = CropReport.query.all()
    report_data = [{"id": r.id, "crop_type": r.crop_type, "lat": r.latitude, "lon": r.longitude, "area_size": r.area_size, "user_id": r.user_id} for r in reports]
    return jsonify(report_data)  # Returns all submitted reports

# 📌 Route: Edit Crop Report
@main_bp.route("/reports/<int:report_id>", methods=["PUT"])
@login_required
def edit_crop_report(report_id):
    report = CropReport.query.get_or_404(report_id)

    # Check if user is the owner or an admin
    if report.user_id != current_user.id and current_user.role != 'admin':
        return jsonify({"error": "You don't have permission to edit this report."}), 403

    if request.content_type.startswith('application/json'):
        data = request.json
    else:
        data = request.form

    if not validate_crop_data(data):
        return jsonify({"error": "Missing or invalid required fields."}), 400

    try:
        report.crop_type = data.get("crop_type")
        report.latitude = float(data.get("latitude"))
        report.longitude = float(data.get("longitude"))
        report.area_size = float(data.get("area_size"))
        report.updated_at = datetime.utcnow()

        db.session.commit()
        return jsonify({"message": "Crop report updated successfully!"}), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": str(e)}), 500

# 📌 Route: Delete Crop Report
@main_bp.route("/reports/<int:report_id>", methods=["DELETE"])
@login_required
def delete_crop_report(report_id):
    report = CropReport.query.get_or_404(report_id)

    # Check if user is the owner or an admin
    if report.user_id != current_user.id and current_user.role != 'admin':
        return jsonify({"error": "You don't have permission to delete this report."}), 403

    try:
        db.session.delete(report)
        db.session.commit()
        return jsonify({"message": "Crop report deleted successfully!"}), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": str(e)}), 500

# 📌 Route: Get User's Crop Reports
@main_bp.route("/my-reports", methods=["GET"])
@login_required
def get_user_reports():
    reports = CropReport.query.filter_by(user_id=current_user.id).all()
    report_data = [{"id": r.id, "crop_type": r.crop_type, "latitude": r.latitude, "longitude": r.longitude, "area_size": r.area_size, "created_at": r.created_at, "updated_at": r.updated_at} for r in reports]
    return jsonify(report_data)

# 📌 Route: User Registration
@main_bp.route("/register", methods=["POST"])
def register():
    data = request.json
    username = data.get("username")
    email = data.get("email")
    password = data.get("password")
    if not username or not email or not password:
        return jsonify({"error": "Missing required fields."}), 400
    if User.query.filter((User.username == username) | (User.email == email)).first():
        return jsonify({"error": "Username or email already exists."}), 400
    password_hash = generate_password_hash(password)
    user = User(username=username, email=email, password_hash=password_hash)
    db.session.add(user)
    db.session.commit()
    return jsonify({"message": "Registration successful!"}), 201

# 📌 Route: User Login (with session management)
@main_bp.route("/login", methods=["POST"])
def login():
    data = request.json
    username = data.get("username")
    password = data.get("password")
    if not username or not password:
        return jsonify({"error": "Missing username or password."}), 400
    user = User.query.filter_by(username=username).first()
    if not user or not check_password_hash(user.password_hash, password):
        return jsonify({"error": "Invalid credentials."), 401
    session["user_id"] = user.id
    return jsonify({"message": f"Welcome, {user.username}!"})

# 📌 Route: User Logout
@main_bp.route("/logout", methods=["POST"])
def logout():
    session.pop("user_id", None)
    return jsonify({"message": "Logged out."})

# 📌 Route: Request Password Reset (placeholder, no email sent)
@main_bp.route("/request-password-reset", methods=["POST"])
def request_password_reset():
    data = request.json
    email = data.get("email")
    user = User.query.filter_by(email=email).first()
    if not user:
        return jsonify({"error": "Email not found."}), 404
    reset_token = secrets.token_urlsafe(16)
    return jsonify({"message": "Password reset requested.", "reset_token": reset_token})

# 📌 Route: Reset Password (placeholder, expects token)
@main_bp.route("/reset-password", methods=["POST"])
def reset_password():
    data = request.json
    email = data.get("email")
    new_password = data.get("new_password")
    reset_token = data.get("reset_token")
    # In a real app, verify token
    user = User.query.filter_by(email=email).first()
    if not user:
        return jsonify({"error": "Email not found."}), 404
    user.password_hash = generate_password_hash(new_password)
    db.session.commit()
    return jsonify({"message": "Password has been reset."})

# 📌 Route: Get User Profile
@main_bp.route("/profile/<username>", methods=["GET"])
def get_profile(username):
    user = User.query.filter_by(username=username).first()
    if not user:
        return jsonify({"error": "User not found."}), 404
    return jsonify({
        "username": user.username,
        "email": user.email,
        "full_name": user.full_name,
        "bio": user.bio,
        "role": user.role,
        "created_at": user.created_at,
    })

# 📌 Route: Update User Profile
@main_bp.route("/profile/<username>", methods=["PUT"])
def update_profile(username):
    user = User.query.filter_by(username=username).first()
    if not user:
        return jsonify({"error": "User not found."}), 404
    data = request.json
    user.full_name = data.get("full_name", user.full_name)
    user.bio = data.get("bio", user.bio)
    db.session.commit()
    return jsonify({"message": "Profile updated."})

# 📌 Route: Email Verification (placeholder, no email sent)
@main_bp.route("/verify-email", methods=["POST"])
def verify_email():
    data = request.json
    email = data.get("email")
    verification_code = data.get("verification_code")
    # In a real app, check code from DB or cache
    # Here, just simulate success
    user = User.query.filter_by(email=email).first()
    if not user:
        return jsonify({"error": "User not found."}), 404
    # Mark user as verified (add field if needed)
    return jsonify({"message": "Email verified!"})

def role_required(role):
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            user_id = session.get("user_id")
            if not user_id:
                return jsonify({"error": "Authentication required."}), 401
            user = User.query.get(user_id)
            if not user or user.role != role:
                return jsonify({"error": "Insufficient permissions."}), 403
            return f(*args, **kwargs)
        return decorated_function
    return decorator

# 📌 Example: Protected admin route
@main_bp.route("/admin-only", methods=["GET"])
@role_required("admin")
def admin_only():
    return jsonify({"message": "Welcome, admin!"})

# 📌 Route: Weather Dashboard
@main_bp.route("/weather")
def weather_dashboard():
    return render_template("weather.html")

# 📌 Route: Analytics Dashboard
@main_bp.route("/analytics")
def analytics_dashboard():
    return render_template("analytics.html")

# 📌 API: Get all crop reports
@main_bp.route("/api/reports", methods=["GET"])
def api_get_reports():
    from app.models import CropReport
    reports = CropReport.query.all()
    return jsonify([
        {
            "id": r.id,
            "crop_type": r.crop_type,
            "latitude": r.latitude,
            "longitude": r.longitude,
            "area_size": r.area_size
        } for r in reports
    ])

# 📌 API: Get all users (basic info)
@main_bp.route("/api/users", methods=["GET"])
def api_get_users():
    users = User.query.all()
    return jsonify([
        {
            "id": u.id,
            "username": u.username,
            "email": u.email,
            "role": u.role
        } for u in users
    ])

# Add validation to field creation
@main_bp.route("/fields", methods=["POST"])
def add_field():
    user_id = session.get("user_id")
    if not user_id:
        return jsonify({"error": "Authentication required."}), 401
    data = request.json if request.is_json else request.form
    name = data.get("name")
    latitude = data.get("latitude")
    longitude = data.get("longitude")
    area_size = data.get("area_size")
    if not name or not latitude or not longitude or not area_size:
        return jsonify({"error": "Missing required fields."}), 400
    try:
        from app.models import Field
        field = Field(
            name=name,
            owner_id=user_id,
            latitude=float(latitude),
            longitude=float(longitude),
            area_size=float(area_size)
        )
        db.session.add(field)
        db.session.commit()
        return jsonify({"message": "Field added!", "field_id": field.id}), 201
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# 📌 Route: List Fields for Current User
@main_bp.route("/fields", methods=["GET"])
def list_fields():
    user_id = session.get("user_id")
    if not user_id:
        return jsonify({"error": "Authentication required."}), 401
    from app.models import Field
    fields = Field.query.filter_by(owner_id=user_id).all()
    return jsonify([
        {
            "id": f.id,
            "name": f.name,
            "latitude": f.latitude,
            "longitude": f.longitude,
            "area_size": f.area_size,
            "created_at": f.created_at
        } for f in fields
    ])

# Add validation to crop calendar creation
@main_bp.route("/crop-calendar", methods=["POST"])
def add_crop_calendar():
    user_id = session.get("user_id")
    if not user_id:
        return jsonify({"error": "Authentication required."}), 401
    data = request.json if request.is_json else request.form
    field_id = data.get("field_id")
    crop_type = data.get("crop_type")
    planting_date = data.get("planting_date")
    if not field_id or not crop_type or not planting_date:
        return jsonify({"error": "Missing required fields."}), 400
    try:
        from app.models import CropCalendar, Field
        # Ensure the field belongs to the user
        field = Field.query.filter_by(id=field_id, owner_id=user_id).first()
        if not field:
            return jsonify({"error": "Field not found or not owned by user."}), 404
        entry = CropCalendar(
            field_id=field_id,
            crop_type=crop_type,
            planting_date=planting_date,
            harvest_date=data.get("harvest_date"),
            notes=data.get("notes")
        )
        db.session.add(entry)
        db.session.commit()
        return jsonify({"message": "Crop calendar entry added!", "calendar_id": entry.id}), 201
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# 📌 Route: List Crop Calendar Entries for User
@main_bp.route("/crop-calendar", methods=["GET"])
def list_crop_calendar():
    user_id = session.get("user_id")
    if not user_id:
        return jsonify({"error": "Authentication required."}), 401
    from app.models import CropCalendar, Field
    fields = Field.query.filter_by(owner_id=user_id).all()
    field_ids = [f.id for f in fields]
    entries = CropCalendar.query.filter(CropCalendar.field_id.in_(field_ids)).all()
    return jsonify([
        {
            "id": e.id,
            "field_id": e.field_id,
            "crop_type": e.crop_type,
            "planting_date": e.planting_date,
            "harvest_date": e.harvest_date,
            "notes": e.notes
        } for e in entries
    ])

# 📌 Route: Batch Import Crop Reports
@main_bp.route("/batch-import", methods=["POST"])
def batch_import():
    user_id = session.get("user_id")
    if not user_id:
        return jsonify({"error": "Authentication required."}), 401
    if 'file' not in request.files:
        return jsonify({"error": "No file uploaded."}), 400
    file = request.files['file']
    if not file.filename.endswith('.csv'):
        return jsonify({"error": "Only CSV files are supported."}), 400
    import csv
    from io import StringIO
    stream = StringIO(file.stream.read().decode("UTF8"))
    reader = csv.DictReader(stream)
    imported, failed = 0, 0
    errors = []
    for row in reader:
        try:
            crop_type = row.get("crop_type")
            latitude = float(row.get("latitude"))
            longitude = float(row.get("longitude"))
            area_size = float(row.get("area_size"))
            if not crop_type or not latitude or not longitude or not area_size:
                raise ValueError("Missing required fields.")
            report = CropReport(
                crop_type=crop_type,
                latitude=latitude,
                longitude=longitude,
                area_size=area_size
            )
            db.session.add(report)
            imported += 1
        except Exception as e:
            failed += 1
            errors.append(str(e))
    db.session.commit()
    return jsonify({
        "imported": imported,
        "failed": failed,
        "errors": errors
    })

# 📌 Route: Export Crop Reports as CSV
@main_bp.route("/export/crop-reports", methods=["GET"])
def export_crop_reports():
    import csv
    from io import StringIO
    reports = CropReport.query.all()
    si = StringIO()
    writer = csv.writer(si)
    writer.writerow(["id", "crop_type", "latitude", "longitude", "area_size", "created_at"])
    for r in reports:
        writer.writerow([r.id, r.crop_type, r.latitude, r.longitude, r.area_size, r.created_at])
    output = si.getvalue()
    from flask import Response
    return Response(
        output,
        mimetype="text/csv",
        headers={"Content-Disposition": "attachment;filename=crop_reports.csv"}
    )

# 📌 Route: Export Fields as CSV
@main_bp.route("/export/fields", methods=["GET"])
def export_fields():
    import csv
    from io import StringIO
    from app.models import Field
    fields = Field.query.all()
    si = StringIO()
    writer = csv.writer(si)
    writer.writerow(["id", "name", "owner_id", "latitude", "longitude", "area_size", "created_at"])
    for f in fields:
        writer.writerow([f.id, f.name, f.owner_id, f.latitude, f.longitude, f.area_size, f.created_at])
    output = si.getvalue()
    from flask import Response
    return Response(
        output,
        mimetype="text/csv",
        headers={"Content-Disposition": "attachment;filename=fields.csv"}
    )

# 📌 Route: Filter Crop Reports
@main_bp.route("/api/reports/filter", methods=["GET"])
def filter_crop_reports():
    crop_type = request.args.get("crop_type")
    min_area = request.args.get("min_area", type=float)
    max_area = request.args.get("max_area", type=float)
    start_date = request.args.get("start_date")
    end_date = request.args.get("end_date")
    query = CropReport.query
    if crop_type:
        query = query.filter(CropReport.crop_type.ilike(f"%{crop_type}%"))
    if min_area is not None:
        query = query.filter(CropReport.area_size >= min_area)
    if max_area is not None:
        query = query.filter(CropReport.area_size <= max_area)
    if start_date:
        query = query.filter(CropReport.created_at >= start_date)
    if end_date:
        query = query.filter(CropReport.created_at <= end_date)
    reports = query.all()
    return jsonify([
        {
            "id": r.id,
            "crop_type": r.crop_type,
            "latitude": r.latitude,
            "longitude": r.longitude,
            "area_size": r.area_size,
            "created_at": r.created_at
        } for r in reports
    ])

# 📌 Route: Get Current Weather (OpenWeatherMap)
@main_bp.route("/api/weather", methods=["GET"])
def get_weather():
    lat = request.args.get("lat")
    lon = request.args.get("lon")
    if not lat or not lon:
        return jsonify({"error": "Missing lat/lon"}), 400
    api_key = "YOUR_OPENWEATHERMAP_API_KEY"  # Replace with your real API key
    url = f"https://api.openweathermap.org/data/2.5/weather?lat={lat}&lon={lon}&appid={api_key}&units=metric"
    try:
        resp = requests.get(url)
        data = resp.json()
        if resp.status_code != 200:
            return jsonify({"error": data.get("message", "Weather API error")}), 502
        return jsonify({
            "location": data.get("name"),
            "weather": data["weather"][0]["main"] if data.get("weather") else None,
            "description": data["weather"][0]["description"] if data.get("weather") else None,
            "temp": data["main"]["temp"] if data.get("main") else None,
            "humidity": data["main"]["humidity"] if data.get("main") else None,
            "wind": data["wind"]["speed"] if data.get("wind") else None
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# 📌 Route: Get Weather Forecast (OpenWeatherMap)
@main_bp.route("/api/forecast", methods=["GET"])
def get_forecast():
    lat = request.args.get("lat")
    lon = request.args.get("lon")
    if not lat or not lon:
        return jsonify({"error": "Missing lat/lon"}), 400
    api_key = "YOUR_OPENWEATHERMAP_API_KEY"  # Replace with your real API key
    url = f"https://api.openweathermap.org/data/2.5/forecast?lat={lat}&lon={lon}&appid={api_key}&units=metric"
    try:
        resp = requests.get(url)
        data = resp.json()
        if resp.status_code != 200:
            return jsonify({"error": data.get("message", "Weather API error")}), 502
        # Return a simplified forecast (next 5 days, 12:00)
        forecast = []
        for entry in data.get("list", []):
            if "12:00:00" in entry["dt_txt"]:
                forecast.append({
                    "date": entry["dt_txt"].split()[0],
                    "temp": entry["main"]["temp"],
                    "weather": entry["weather"][0]["main"],
                    "description": entry["weather"][0]["description"]
                })
        return jsonify(forecast)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# 📌 Route: Get Weather-Based Agricultural Advice
@main_bp.route("/api/weather/advice", methods=["GET"])
def get_weather_advice():
    lat = request.args.get("lat")
    lon = request.args.get("lon")
    crop_type = request.args.get("crop_type")

    if not lat or not lon or not crop_type:
        return jsonify({"error": "Missing lat/lon or crop type"}), 400

    try:
        # Get current weather data
        api_key = "YOUR_OPENWEATHERMAP_API_KEY"  # Replace with your real API key
        url = f"https://api.openweathermap.org/data/2.5/weather?lat={lat}&lon={lon}&appid={api_key}&units=metric"
        resp = requests.get(url)
        data = resp.json()

        if resp.status_code != 200:
            return jsonify({"error": data.get("message", "Weather API error")}), 502

        # Extract relevant weather data
        weather = {
            "temp": data["main"]["temp"],
            "humidity": data["main"]["humidity"],
            "wind_speed": data["wind"]["speed"],
            "description": data["weather"][0]["description"],
            "clouds": data.get("clouds", {}).get("all", 0),
            "rain": data.get("rain", {}).get("1h", 0)  # Rain volume for last hour
        }

        # Generate advice based on crop type and weather conditions
        advice = []

        # Temperature advice
        if crop_type == "wheat":
            if weather["temp"] < 5:
                advice.append("Warning: Temperature below optimal range for wheat growth (5-25°C). Consider protective measures.")
            elif weather["temp"] > 25:
                advice.append("Warning: Temperature above optimal range for wheat. Ensure adequate irrigation.")
            else:
                advice.append("Temperature is within optimal range for wheat growth.")

        elif crop_type == "cotton":
            if weather["temp"] < 15:
                advice.append("Warning: Temperature too low for cotton growth (optimal 15-30°C). Monitor crop health.")
            elif weather["temp"] > 30:
                advice.append("Warning: Temperature above optimal range for cotton. Ensure sufficient irrigation and consider shade measures.")
            else:
                advice.append("Temperature is within optimal range for cotton growth.")

        elif crop_type == "rice":
            if weather["temp"] < 20:
                advice.append("Warning: Temperature below optimal range for rice (20-35°C). Monitor crop development.")
            elif weather["temp"] > 35:
                advice.append("Warning: Temperature above optimal range for rice. Maintain proper water levels.")
            else:
                advice.append("Temperature is within optimal range for rice growth.")

        elif crop_type == "corn":
            if weather["temp"] < 10:
                advice.append("Warning: Temperature below optimal range for corn growth (10-32°C). Delay planting or protect young plants.")
            elif weather["temp"] > 32:
                advice.append("Warning: Temperature above optimal range for corn. Ensure adequate irrigation to prevent stress.")
            else:
                advice.append("Temperature is within optimal range for corn growth.")

        elif crop_type == "vegetables":
            if weather["temp"] < 10:
                advice.append("Warning: Temperature too low for most vegetables. Consider protective measures or greenhouse cultivation.")
            elif weather["temp"] > 30:
                advice.append("Warning: High temperatures may stress vegetables. Provide shade and increase watering frequency.")
            else:
                advice.append("Temperature is generally suitable for vegetable growth, but specific requirements vary by crop.")

        elif crop_type == "fruits":
            if weather["temp"] < 7:
                advice.append("Warning: Low temperatures may damage fruit trees/plants. Monitor for frost damage.")
            elif weather["temp"] > 35:
                advice.append("Warning: Extreme heat may cause sunburn on fruits. Consider shade nets and increased irrigation.")
            else:
                advice.append("Temperature is generally suitable for fruit development, but specific requirements vary by fruit type.")

        # Humidity advice
        if weather["humidity"] < 40:
            advice.append("Low humidity conditions. Consider irrigation to maintain soil moisture.")
        elif weather["humidity"] > 80:
            advice.append("High humidity may increase disease risk. Monitor for fungal diseases.")

        # Wind advice
        if weather["wind_speed"] > 10:
            advice.append("Strong winds detected. Consider wind protection measures.")

        # Rain/Clouds advice
        if weather["rain"] > 0:
            advice.append("Recent rainfall detected. Adjust irrigation schedules accordingly.")
        elif weather["clouds"] > 80:
            advice.append("Heavy cloud cover may reduce photosynthesis. Monitor crop growth.")

        # General advice based on weather description
        if "rain" in weather["description"]:
            advice.append("Rainy conditions: Check field drainage and pest monitoring.")
        elif "clear" in weather["description"]:
            advice.append("Clear weather: Good conditions for field operations and pesticide application if needed.")

        return jsonify({
            "crop_type": crop_type,
            "current_weather": weather,
            "advice": advice
        })

    except Exception as e:
        return jsonify({"error": str(e)}), 500

# 📌 Route: Get Heatmap Data for Visualizations
@main_bp.route("/api/heatmap", methods=["GET"])
def get_heatmap_data():
    crop_type = request.args.get("crop_type")
    query = CropReport.query

    if crop_type:
        query = query.filter(CropReport.crop_type == crop_type)

    reports = query.all()
    from app.utils import generate_heatmap_data
    heatmap_data = generate_heatmap_data(reports)

    return jsonify(heatmap_data)

# 📌 Route: Get Choropleth Map Data (Aggregated by Region)
@main_bp.route("/api/choropleth", methods=["GET"])
def get_choropleth_data():
    from sqlalchemy import func
    crop_type = request.args.get("crop_type")
    metric = request.args.get("metric", "area")  # area or count

    # Base query to get data points
    query = CropReport.query

    if crop_type:
        query = query.filter(CropReport.crop_type == crop_type)

    # Get data points and find which region they belong to
    reports = query.all()
    from app.utils import get_region_for_coordinates

    # Aggregate data by region
    region_data = {}
    for report in reports:
        region = get_region_for_coordinates(report.latitude, report.longitude)
        if region not in region_data:
            region_data[region] = {
                "area": 0,
                "count": 0
            }
        region_data[region]["area"] += report.area_size
        region_data[region]["count"] += 1

    # Format data as GeoJSON
    features = []
    from app.utils import get_region_boundaries

    for region, data in region_data.items():
        boundaries = get_region_boundaries(region)
        if boundaries:
            feature = {
                "type": "Feature",
                "properties": {
                    "name": region,
                    "area": data["area"],
                    "count": data["count"],
                    "value": data["area"] if metric == "area" else data["count"]
                },
                "geometry": boundaries
            }
            features.append(feature)

    geojson = {
        "type": "FeatureCollection",
        "features": features
    }

    return jsonify(geojson)

# 📌 Route: Get Time Series Data
@main_bp.route("/api/timeseries", methods=["GET"])
def get_timeseries_data():
    from sqlalchemy import func
    crop_type = request.args.get("crop_type")
    interval = request.args.get("interval", "month")  # day, week, month, year
    start_date = request.args.get("start_date")
    end_date = request.args.get("end_date")

    # Base query to get data points
    query = CropReport.query

    if crop_type:
        query = query.filter(CropReport.crop_type == crop_type)
    if start_date:
        query = query.filter(CropReport.created_at >= start_date)
    if end_date:
        query = query.filter(CropReport.created_at <= end_date)

    # Group by time interval
    if interval == "day":
        grouping = func.date(CropReport.created_at)
    elif interval == "week":
        grouping = func.date_trunc("week", CropReport.created_at)
    elif interval == "year":
        grouping = func.date_trunc("year", CropReport.created_at)
    else:  # default to month
        grouping = func.date_trunc("month", CropReport.created_at)

    # Get aggregated data
    results = (
        query.with_entities(
            grouping.label("date"),
            func.sum(CropReport.area_size).label("total_area"),
            func.count().label("report_count")
        )
        .group_by(grouping)
        .order_by(grouping)
        .all()
    )

    # Format response
    data = [{
        "date": result.date.isoformat(),
        "total_area": float(result.total_area),
        "report_count": result.report_count
    } for result in results]

    return jsonify(data)

# 📌 Prediction Routes

# 📌 Route: Prediction Models Management
@main_bp.route("/api/prediction-models", methods=["GET"])
def get_prediction_models():
    """Get all prediction models"""
    from app.models import PredictionModel
    models = PredictionModel.query.all()
    return jsonify([{
        "id": model.id,
        "name": model.name,
        "model_type": model.model_type,
        "description": model.description,
        "accuracy": model.accuracy,
        "created_at": model.created_at.isoformat() if model.created_at else None
    } for model in models])

@main_bp.route("/api/prediction-models", methods=["POST"])
@login_required
def create_prediction_model():
    """Create a new prediction model (admin only)"""
    if current_user.role != 'admin':
        return jsonify({"error": "Admin access required"}), 403

    data = request.json

    try:
        from app.models import PredictionModel
        model = PredictionModel(
            name=data.get("name"),
            model_type=data.get("model_type"),
            description=data.get("description"),
            parameters=data.get("parameters", {}),
            accuracy=data.get("accuracy")
        )
        db.session.add(model)
        db.session.commit()
        return jsonify({
            "message": "Prediction model created successfully",
            "model_id": model.id
        }), 201
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": str(e)}), 500

# 📌 Route: Crop Yield Prediction
@main_bp.route("/api/predict/yield", methods=["POST"])
@login_required
def predict_yield():
    """Predict crop yield for a field"""
    data = request.json

    # Validate required fields
    required_fields = ["field_id", "crop_type"]
    if not all(field in data for field in required_fields):
        return jsonify({"error": "Missing required fields"}), 400

    field_id = data.get("field_id")
    crop_type = data.get("crop_type")

    # Get weather data (from request or fetch from API)
    weather_data = data.get("weather_data", {})
    if not weather_data:
        # If weather data not provided, try to fetch it
        from app.models import Field
        field = Field.query.get(field_id)
        if not field:
            return jsonify({"error": "Field not found"}), 404

        # Fetch weather data for field location
        try:
            api_key = "YOUR_OPENWEATHERMAP_API_KEY"  # Replace with your real API key
            url = f"https://api.openweathermap.org/data/2.5/weather?lat={field.latitude}&lon={field.longitude}&appid={api_key}&units=metric"
            resp = requests.get(url)
            if resp.status_code == 200:
                weather_json = resp.json()
                weather_data = {
                    "avg_temperature": weather_json["main"]["temp"],
                    "humidity": weather_json["main"]["humidity"],
                    "rainfall": weather_json.get("rain", {}).get("1h", 0) * 24  # Convert to daily rainfall
                }
            else:
                # Use default weather data if API call fails
                weather_data = {
                    "avg_temperature": 20,
                    "humidity": 50,
                    "rainfall": 100
                }
        except Exception as e:
            # Use default weather data if API call fails
            weather_data = {
                "avg_temperature": 20,
                "humidity": 50,
                "rainfall": 100
            }

    # Get soil data if provided
    soil_data = data.get("soil_data")

    # Call prediction function
    from app.utils import predict_crop_yield
    prediction_result = predict_crop_yield(crop_type, field_id, weather_data, soil_data)

    # Store prediction in database
    try:
        from app.models import Prediction, PredictionModel

        # Get or create a default prediction model
        model = PredictionModel.query.filter_by(model_type="yield").first()
        if not model:
            model = PredictionModel(
                name="Default Yield Model",
                model_type="yield",
                description="Basic yield prediction model",
                parameters={},
                accuracy=0.7
            )
            db.session.add(model)
            db.session.commit()

        # Create prediction record
        prediction = Prediction(
            model_id=model.id,
            field_id=field_id,
            crop_type=crop_type,
            prediction_type="yield",
            prediction_value=prediction_result.get("predicted_yield", 0),
            confidence_score=prediction_result.get("confidence_score", 0.5),
            input_parameters={
                "weather_data": weather_data,
                "soil_data": soil_data
            }
        )
        db.session.add(prediction)
        db.session.commit()

        # Add prediction ID to result
        prediction_result["prediction_id"] = prediction.id

    except Exception as e:
        db.session.rollback()
        # Still return prediction result even if saving fails
        prediction_result["warning"] = f"Prediction calculated but not saved: {str(e)}"

    return jsonify(prediction_result)

# 📌 Route: Disease Risk Prediction
@main_bp.route("/api/predict/disease-risk", methods=["POST"])
@login_required
def predict_disease():
    """Predict disease risk for a crop in a field"""
    data = request.json

    # Validate required fields
    required_fields = ["field_id", "crop_type"]
    if not all(field in data for field in required_fields):
        return jsonify({"error": "Missing required fields"}), 400

    field_id = data.get("field_id")
    crop_type = data.get("crop_type")

    # Get weather data (from request or fetch from API)
    weather_data = data.get("weather_data", {})
    if not weather_data:
        # If weather data not provided, try to fetch it
        from app.models import Field
        field = Field.query.get(field_id)
        if not field:
            return jsonify({"error": "Field not found"}), 404

        # Fetch weather data for field location
        try:
            api_key = "YOUR_OPENWEATHERMAP_API_KEY"  # Replace with your real API key
            url = f"https://api.openweathermap.org/data/2.5/weather?lat={field.latitude}&lon={field.longitude}&appid={api_key}&units=metric"
            resp = requests.get(url)
            if resp.status_code == 200:
                weather_json = resp.json()
                weather_data = {
                    "avg_temperature": weather_json["main"]["temp"],
                    "humidity": weather_json["main"]["humidity"],
                    "rainfall": weather_json.get("rain", {}).get("1h", 0) * 24  # Convert to daily rainfall
                }
            else:
                # Use default weather data if API call fails
                weather_data = {
                    "avg_temperature": 20,
                    "humidity": 50,
                    "rainfall": 100
                }
        except Exception as e:
            # Use default weather data if API call fails
            weather_data = {
                "avg_temperature": 20,
                "humidity": 50,
                "rainfall": 100
            }

    # Call prediction function
    from app.utils import predict_disease_risk
    prediction_result = predict_disease_risk(crop_type, field_id, weather_data)

    # Store prediction in database
    try:
        from app.models import Prediction, PredictionModel

        # Get or create a default prediction model
        model = PredictionModel.query.filter_by(model_type="disease").first()
        if not model:
            model = PredictionModel(
                name="Default Disease Risk Model",
                model_type="disease",
                description="Basic disease risk prediction model",
                parameters={},
                accuracy=0.65
            )
            db.session.add(model)
            db.session.commit()

        # Create prediction record for each disease risk
        for disease_risk in prediction_result.get("disease_risks", []):
            prediction = Prediction(
                model_id=model.id,
                field_id=field_id,
                crop_type=crop_type,
                prediction_type=f"disease_risk_{disease_risk['disease']}",
                prediction_value=disease_risk.get("risk", 0),
                confidence_score=disease_risk.get("confidence", 0.5),
                input_parameters={
                    "weather_data": weather_data,
                    "disease": disease_risk["disease"]
                }
            )
            db.session.add(prediction)

        db.session.commit()

    except Exception as e:
        db.session.rollback()
        # Still return prediction result even if saving fails
        prediction_result["warning"] = f"Prediction calculated but not saved: {str(e)}"

    return jsonify(prediction_result)

# 📌 Route: Crop Recommendations
@main_bp.route("/api/predict/crop-recommendations", methods=["GET"])
@login_required
def get_crop_recommendations():
    """Get crop recommendations for a field"""
    field_id = request.args.get("field_id")
    if not field_id:
        return jsonify({"error": "Field ID is required"}), 400

    # Call recommendation function
    from app.utils import generate_crop_recommendations
    recommendations = generate_crop_recommendations(field_id)

    return jsonify(recommendations)

# 📌 Prediction Visualization Routes

@main_bp.route("/predictions")
def predictions_dashboard():
    """Render the predictions dashboard page"""
    return render_template("predictions.html")

@main_bp.route("/api/visualization/yield-predictions", methods=["GET"])
def visualize_yield_predictions():
    """Get data for yield prediction visualizations"""
    crop_type = request.args.get("crop_type")
    region = request.args.get("region")
    start_date = request.args.get("start_date")
    end_date = request.args.get("end_date")

    from app.utils import analyze_crop_yields
    analysis = analyze_crop_yields(crop_type, region, start_date, end_date)

    # Format data for visualization
    visualization_data = {
        "chart_data": {
            "bar_chart": [],
            "line_chart": [],
            "pie_chart": []
        },
        "statistics": analysis.get("overall_statistics", {}),
        "crop_statistics": analysis.get("crop_statistics", {})
    }

    # Format data for bar chart (by crop type)
    for crop, stats in analysis.get("crop_statistics", {}).items():
        if "mean" in stats:
            visualization_data["chart_data"]["bar_chart"].append({
                "label": crop,
                "value": stats["mean"],
                "min": stats.get("min"),
                "max": stats.get("max")
            })

    # Return visualization data
    return jsonify(visualization_data)

@main_bp.route("/api/visualization/disease-risk", methods=["GET"])
def visualize_disease_risk():
    """Get data for disease risk visualizations"""
    crop_type = request.args.get("crop_type")
    disease = request.args.get("disease")
    region = request.args.get("region")
    start_date = request.args.get("start_date")
    end_date = request.args.get("end_date")

    from app.utils import analyze_disease_risk
    analysis = analyze_disease_risk(crop_type, disease, region, start_date, end_date)

    # Format data for visualization
    visualization_data = {
        "chart_data": {
            "heatmap": [],
            "radar_chart": [],
            "bar_chart": []
        },
        "statistics": analysis.get("overall_statistics", {}),
        "disease_statistics": analysis.get("disease_statistics", {})
    }

    # Format data for radar chart (by disease)
    radar_data = {
        "labels": [],
        "datasets": []
    }

    for disease_name, stats in analysis.get("disease_statistics", {}).items():
        if "mean" in stats:
            radar_data["labels"].append(disease_name)
            visualization_data["chart_data"]["bar_chart"].append({
                "label": disease_name,
                "value": stats["mean"],
                "min": stats.get("min"),
                "max": stats.get("max")
            })

    # Add radar dataset for each crop type
    for crop, stats in analysis.get("crop_statistics", {}).items():
        crop_data = {
            "label": crop,
            "data": []
        }
        for disease_name in radar_data["labels"]:
            # Find the risk value for this crop and disease
            risk_value = 0
            for r in analysis.get("disease_statistics", {}).get(disease_name, {}).get("data", []):
                if r.get("crop_type") == crop:
                    risk_value = r.get("risk", 0)
                    break
            crop_data["data"].append(risk_value)

        radar_data["datasets"].append(crop_data)

    visualization_data["chart_data"]["radar_chart"] = radar_data

    # Return visualization data
    return jsonify(visualization_data)

@main_bp.route("/api/visualization/weather-impact", methods=["GET"])
def visualize_weather_impact():
    """Get data for weather impact visualizations"""
    crop_type = request.args.get("crop_type")
    weather_factor = request.args.get("weather_factor", "temperature")
    start_date = request.args.get("start_date")
    end_date = request.args.get("end_date")

    from app.utils import analyze_weather_impact
    analysis = analyze_weather_impact(crop_type, weather_factor, start_date, end_date)

    # Format data for visualization
    visualization_data = {
        "chart_data": {
            "scatter_plot": [],
            "line_chart": []
        },
        "correlation": analysis.get("correlation"),
        "interpretation": analysis.get("interpretation"),
        "binned_analysis": analysis.get("binned_analysis", {})
    }

    # Format data for scatter plot
    if "weather_values" in analysis and "yield_values" in analysis:
        for weather, yield_val in zip(analysis["weather_values"], analysis["yield_values"]):
            visualization_data["chart_data"]["scatter_plot"].append({
                "x": weather,
                "y": yield_val
            })

    # Format data for line chart (binned analysis)
    for bin_range, avg_yield in analysis.get("binned_analysis", {}).items():
        if avg_yield is not None:
            visualization_data["chart_data"]["line_chart"].append({
                "label": bin_range,
                "value": avg_yield
            })

    # Return visualization data
    return jsonify(visualization_data)

@main_bp.route("/api/visualization/prediction-trends", methods=["GET"])
def visualize_prediction_trends():
    """Get data for prediction trend visualizations"""
    crop_type = request.args.get("crop_type")
    prediction_type = request.args.get("prediction_type", "yield")
    interval = request.args.get("interval", "month")
    start_date = request.args.get("start_date")
    end_date = request.args.get("end_date")

    from app.models import Prediction, db
    from sqlalchemy import func
    from datetime import datetime, timedelta

    # Set default date range if not provided
    if not end_date:
        end_date = datetime.utcnow().date()
    if not start_date:
        start_date = end_date - timedelta(days=365)  # Default to 1 year of data

    # Base query
    query = db.session.query(
        func.date_trunc(interval, Prediction.created_at).label('date_group'),
        func.avg(Prediction.prediction_value).label('avg_value'),
        func.count().label('count')
    ).filter(
        Prediction.created_at >= start_date,
        Prediction.created_at <= end_date
    )

    # Apply filters
    if crop_type:
        query = query.filter(Prediction.crop_type == crop_type)

    if prediction_type == "yield":
        query = query.filter(Prediction.prediction_type == "yield")
    elif prediction_type == "disease":
        query = query.filter(Prediction.prediction_type.like("disease_risk_%"))

    # Group and order
    query = query.group_by('date_group').order_by('date_group')

    # Execute query
    results = query.all()

    # Format data for visualization
    trend_data = []
    for result in results:
        trend_data.append({
            "date": result.date_group.isoformat() if hasattr(result.date_group, 'isoformat') else str(result.date_group),
            "value": float(result.avg_value),
            "count": result.count
        })

    # Return visualization data
    return jsonify({
        "trend_data": trend_data,
        "prediction_type": prediction_type,
        "interval": interval,
        "crop_type": crop_type,
        "date_range": {
            "start": start_date.isoformat() if hasattr(start_date, 'isoformat') else start_date,
            "end": end_date.isoformat() if hasattr(end_date, 'isoformat') else end_date
        }
    })

# 📌 Route: Data Visualization Dashboard
@main_bp.route("/visualization")
def visualization():
    return render_template("visualization.html")

# 📌 Prediction Validation Routes

@main_bp.route("/api/validate/model/<int:model_id>", methods=["GET"])
@login_required
def validate_model(model_id):
    """Validate a prediction model using historical data"""
    validation_method = request.args.get("method", "cross_validation")
    folds = request.args.get("folds", 5, type=int)

    from app.utils import validate_prediction_model
    validation_results = validate_prediction_model(model_id, validation_method=validation_method, folds=folds)

    return jsonify(validation_results)

@main_bp.route("/api/validate/input", methods=["POST"])
def validate_input():
    """Validate input data for prediction models"""
    data = request.json
    prediction_type = data.get("prediction_type", "yield")

    from app.utils import validate_prediction_input
    is_valid, errors = validate_prediction_input(data, prediction_type)

    return jsonify({
        "valid": is_valid,
        "errors": errors
    })

@main_bp.route("/api/validate/confidence", methods=["POST"])
def get_confidence():
    """Get confidence score for a prediction"""
    data = request.json
    prediction_value = data.get("prediction_value")
    prediction_type = data.get("prediction_type", "yield")

    if prediction_value is None:
        return jsonify({"error": "Missing prediction_value"}), 400

    try:
        prediction_value = float(prediction_value)
    except (ValueError, TypeError):
        return jsonify({"error": "prediction_value must be a number"}), 400

    from app.utils import get_prediction_confidence
    confidence = get_prediction_confidence(prediction_value, prediction_type)

    return jsonify({
        "prediction_value": prediction_value,
        "prediction_type": prediction_type,
        "confidence_score": confidence
    })

# 📌 Trend Analysis Routes

@main_bp.route("/api/trends/predictions", methods=["GET"])
def analyze_trends():
    """Analyze trends in predictions over time"""
    prediction_type = request.args.get("prediction_type", "yield")
    crop_type = request.args.get("crop_type")
    interval = request.args.get("interval", "month")
    start_date = request.args.get("start_date")
    end_date = request.args.get("end_date")

    from app.utils import analyze_prediction_trends
    trend_analysis = analyze_prediction_trends(
        prediction_type=prediction_type,
        crop_type=crop_type,
        start_date=start_date,
        end_date=end_date,
        interval=interval
    )

    return jsonify(trend_analysis)

@main_bp.route("/api/trends/forecast", methods=["POST"])
def forecast_trends():
    """Forecast future values based on historical trends"""
    data = request.json
    time_series = data.get("time_series", [])
    periods = data.get("periods", 6)
    method = data.get("method", "linear")

    from app.utils import forecast_future_values
    forecast = forecast_future_values(time_series, periods, method)

    return jsonify({
        "forecast": forecast,
        "method": method,
        "periods": periods
    })

@main_bp.route("/api/trends/accuracy", methods=["GET"])
def analyze_accuracy():
    """Compare predictions with actual values to evaluate accuracy over time"""
    prediction_type = request.args.get("prediction_type", "yield")
    start_date = request.args.get("start_date")
    end_date = request.args.get("end_date")

    from app.utils import compare_predictions_with_actuals
    comparison = compare_predictions_with_actuals(
        prediction_type=prediction_type,
        start_date=start_date,
        end_date=end_date
    )

    return jsonify(comparison)

# 📌 Alert System Routes

@main_bp.route("/api/alerts", methods=["GET"])
@login_required
def get_alerts():
    """Get alerts for the current user"""
    include_read = request.args.get("include_read", "false").lower() == "true"
    limit = request.args.get("limit", 50, type=int)

    from app.utils import get_user_alerts
    alerts = get_user_alerts(current_user.id, include_read, limit)

    return jsonify([{
        "id": alert.id,
        "alert_type": alert.alert_type,
        "severity": alert.severity,
        "message": alert.message,
        "details": alert.details,
        "is_read": alert.is_read,
        "created_at": alert.created_at.isoformat(),
        "expires_at": alert.expires_at.isoformat() if alert.expires_at else None,
        "field_id": alert.field_id
    } for alert in alerts])

@main_bp.route("/api/alerts/<int:alert_id>/read", methods=["POST"])
@login_required
def mark_alert_read(alert_id):
    """Mark an alert as read"""
    from app.utils import mark_alert_as_read
    success = mark_alert_as_read(alert_id, current_user.id)

    if success:
        return jsonify({"message": "Alert marked as read"}), 200
    else:
        return jsonify({"error": "Failed to mark alert as read"}), 400

@main_bp.route("/api/alert-rules", methods=["GET"])
@login_required
def get_alert_rules():
    """Get alert rules for the current user"""
    from app.models import AlertRule

    rules = AlertRule.query.filter_by(user_id=current_user.id).all()

    return jsonify([{
        "id": rule.id,
        "name": rule.name,
        "alert_type": rule.alert_type,
        "field_id": rule.field_id,
        "crop_type": rule.crop_type,
        "condition_type": rule.condition_type,
        "condition_value": rule.condition_value,
        "condition_operator": rule.condition_operator,
        "severity": rule.severity,
        "is_active": rule.is_active,
        "created_at": rule.created_at.isoformat()
    } for rule in rules])

@main_bp.route("/api/alert-rules", methods=["POST"])
@login_required
def create_alert_rule():
    """Create a new alert rule"""
    data = request.json

    # Validate required fields
    required_fields = ["name", "alert_type", "condition_type", "condition_value", "condition_operator", "severity"]
    for field in required_fields:
        if field not in data:
            return jsonify({"error": f"Missing required field: {field}"}), 400

    try:
        from app.models import AlertRule, db

        rule = AlertRule(
            user_id=current_user.id,
            name=data["name"],
            alert_type=data["alert_type"],
            field_id=data.get("field_id"),
            crop_type=data.get("crop_type"),
            condition_type=data["condition_type"],
            condition_value=float(data["condition_value"]),
            condition_operator=data["condition_operator"],
            severity=data["severity"],
            is_active=data.get("is_active", True)
        )

        db.session.add(rule)
        db.session.commit()

        return jsonify({
            "message": "Alert rule created successfully",
            "rule_id": rule.id
        }), 201
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": str(e)}), 500

@main_bp.route("/api/alert-rules/<int:rule_id>", methods=["PUT"])
@login_required
def update_alert_rule(rule_id):
    """Update an alert rule"""
    from app.models import AlertRule, db

    rule = AlertRule.query.get(rule_id)
    if not rule:
        return jsonify({"error": "Alert rule not found"}), 404

    # Check ownership
    if rule.user_id != current_user.id:
        return jsonify({"error": "You don't have permission to update this rule"}), 403

    data = request.json

    # Update fields
    if "name" in data:
        rule.name = data["name"]
    if "alert_type" in data:
        rule.alert_type = data["alert_type"]
    if "field_id" in data:
        rule.field_id = data["field_id"]
    if "crop_type" in data:
        rule.crop_type = data["crop_type"]
    if "condition_type" in data:
        rule.condition_type = data["condition_type"]
    if "condition_value" in data:
        rule.condition_value = float(data["condition_value"])
    if "condition_operator" in data:
        rule.condition_operator = data["condition_operator"]
    if "severity" in data:
        rule.severity = data["severity"]
    if "is_active" in data:
        rule.is_active = data["is_active"]

    try:
        db.session.commit()
        return jsonify({"message": "Alert rule updated successfully"}), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": str(e)}), 500

@main_bp.route("/api/alert-rules/<int:rule_id>", methods=["DELETE"])
@login_required
def delete_alert_rule(rule_id):
    """Delete an alert rule"""
    from app.models import AlertRule, db

    rule = AlertRule.query.get(rule_id)
    if not rule:
        return jsonify({"error": "Alert rule not found"}), 404

    # Check ownership
    if rule.user_id != current_user.id:
        return jsonify({"error": "You don't have permission to delete this rule"}), 403

    try:
        db.session.delete(rule)
        db.session.commit()
        return jsonify({"message": "Alert rule deleted successfully"}), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": str(e)}), 500

@main_bp.route("/api/check-alerts", methods=["POST"])
@login_required
def check_alerts():
    """Manually check alert conditions for the current user"""
    from app.utils import check_alert_conditions

    new_alerts = check_alert_conditions(current_user.id)

    return jsonify({
        "message": f"{len(new_alerts)} new alerts generated",
        "alert_count": len(new_alerts)
    })

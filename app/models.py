from app import db
from datetime import datetime

class User(db.Model):
    __tablename__ = 'user'
    
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(64), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(128), nullable=False)
    role = db.Column(db.String(32), default='user')
    full_name = db.Column(db.String(120))
    bio = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def __repr__(self):
        return f'<User {self.username}>'

class CropReport(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    crop_type = db.Column(db.String(64), nullable=False)
    latitude = db.Column(db.Float, nullable=False)
    longitude = db.Column(db.Float, nullable=False)
    area_size = db.Column(db.Float, nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    user = db.relationship('User', backref=db.backref('crop_reports', lazy=True))

    def __repr__(self):
        return f'<CropReport {self.crop_type} ({self.latitude}, {self.longitude})>'

class Field(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(128), nullable=False)
    owner_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    latitude = db.Column(db.Float, nullable=False)
    longitude = db.Column(db.Float, nullable=False)
    area_size = db.Column(db.Float, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    owner = db.relationship('User', backref=db.backref('fields', lazy=True))

    def __repr__(self):
        return f'<Field {self.name} ({self.latitude}, {self.longitude})>'

class CropCalendar(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    field_id = db.Column(db.Integer, db.ForeignKey('field.id'), nullable=False)
    crop_type = db.Column(db.String(64), nullable=False)
    planting_date = db.Column(db.Date, nullable=False)
    harvest_date = db.Column(db.Date, nullable=True)
    notes = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    field = db.relationship('Field', backref=db.backref('crop_calendars', lazy=True))

    def __repr__(self):
        return f'<CropCalendar {self.crop_type} ({self.planting_date})>'

class PredictionModel(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(128), nullable=False)
    model_type = db.Column(db.String(64), nullable=False)  # yield, disease, weather, etc.
    description = db.Column(db.Text)
    parameters = db.Column(db.JSON)  # Store model parameters as JSON
    accuracy = db.Column(db.Float)  # Model accuracy metric
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def __repr__(self):
        return f'<PredictionModel {self.name} ({self.model_type})>'

class Prediction(db.Model):
    __tablename__ = 'prediction'
    __table_args__ = {'extend_existing': True}
    
    id = db.Column(db.Integer, primary_key=True)
    crop_id = db.Column(db.Integer, db.ForeignKey('crop.id'), nullable=False)
    prediction_type = db.Column(db.String(64), nullable=False)
    value = db.Column(db.Float, nullable=False)
    confidence = db.Column(db.Float, nullable=False)
    factors = db.Column(db.JSON)
    valid_from = db.Column(db.DateTime, nullable=False)
    valid_to = db.Column(db.DateTime, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    crop = db.relationship('Crop', backref=db.backref('predictions', lazy=True))

    def __repr__(self):
        return f'<Prediction {self.prediction_type} for Crop {self.crop_id}>'

class Alert(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    field_id = db.Column(db.Integer, db.ForeignKey('field.id'), nullable=True)
    alert_type = db.Column(db.String(64), nullable=False)  # weather, disease, yield, etc.
    severity = db.Column(db.String(32), nullable=False)  # info, warning, danger
    message = db.Column(db.Text, nullable=False)
    details = db.Column(db.JSON)  # Additional details as JSON
    is_read = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    expires_at = db.Column(db.DateTime, nullable=True)

    user = db.relationship('User', backref=db.backref('alerts', lazy=True))
    field = db.relationship('Field', backref=db.backref('alerts', lazy=True))

    def __repr__(self):
        return f'<Alert {self.alert_type} ({self.severity})>'

class AlertRule(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    name = db.Column(db.String(128), nullable=False)
    alert_type = db.Column(db.String(64), nullable=False)  # weather, disease, yield, etc.
    field_id = db.Column(db.Integer, db.ForeignKey('field.id'), nullable=True)  # If null, applies to all fields
    crop_type = db.Column(db.String(64), nullable=True)  # If null, applies to all crops
    condition_type = db.Column(db.String(64), nullable=False)  # threshold, change, anomaly
    condition_value = db.Column(db.Float, nullable=False)  # Threshold value
    condition_operator = db.Column(db.String(16), nullable=False)  # >, <, =, >=, <=
    severity = db.Column(db.String(32), nullable=False)  # info, warning, danger
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    user = db.relationship('User', backref=db.backref('alert_rules', lazy=True))
    field = db.relationship('Field', backref=db.backref('alert_rules', lazy=True))

    def __repr__(self):
        return f'<AlertRule {self.name} ({self.alert_type})>'

class Crop(db.Model):
    __tablename__ = 'crop'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(128), nullable=False)
    type = db.Column(db.String(64), nullable=False)
    planted_date = db.Column(db.Date, nullable=False)
    field_id = db.Column(db.Integer, db.ForeignKey('field.id'), nullable=False)
    status = db.Column(db.String(32), default='active')
    notes = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    field = db.relationship('Field', backref=db.backref('crops', lazy=True))

    def __repr__(self):
        return f'<Crop {self.name} in Field {self.field_id}>'

class Weather(db.Model):
    __tablename__ = 'weather'
    
    id = db.Column(db.Integer, primary_key=True)
    latitude = db.Column(db.Float, nullable=False)
    longitude = db.Column(db.Float, nullable=False)
    temperature = db.Column(db.Float, nullable=False)
    humidity = db.Column(db.Float, nullable=False)
    precipitation = db.Column(db.Float, nullable=False)
    wind_speed = db.Column(db.Float, nullable=False)
    wind_direction = db.Column(db.Float, nullable=False)
    timestamp = db.Column(db.DateTime, nullable=False)
    forecast_time = db.Column(db.DateTime, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def __repr__(self):
        return f'<Weather ({self.latitude}, {self.longitude}) at {self.timestamp}>'

from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from app import db
from datetime import datetime
import uuid

class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(64), index=True, unique=True, nullable=False)
    email = db.Column(db.String(120), index=True, unique=True, nullable=False)
    password_hash = db.Column(db.String(128))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    is_active = db.Column(db.Boolean, default=True)
    is_admin = db.Column(db.Boolean, default=False)
    last_seen = db.Column(db.DateTime, default=datetime.utcnow)
    reset_token = db.Column(db.String(100), unique=True)
    
    # Relationships
    crop_reports = db.relationship('CropReport', backref='author', lazy='dynamic')
    map_suggestions = db.relationship('MapSuggestion', backref='author', lazy='dynamic')
    
    def set_password(self, password):
        self.password_hash = generate_password_hash(password)
        
    def check_password(self, password):
        return check_password_hash(self.password_hash, password)
        
    def generate_reset_token(self):
        self.reset_token = str(uuid.uuid4())
        return self.reset_token
        
    def __repr__(self):
        return f'<User {self.username}>'

# Update existing models
class CropReport(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    crop_type = db.Column(db.String(100), nullable=False)
    field_size = db.Column(db.Float, nullable=False)
    latitude = db.Column(db.Float, nullable=False)
    longitude = db.Column(db.Float, nullable=False)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    planting_date = db.Column(db.Date, nullable=True)
    field_boundary = db.Column(db.JSON, nullable=True)  # Store GeoJSON
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    public = db.Column(db.Boolean, default=True)  # Whether visible to other users

class WeatherData(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    latitude = db.Column(db.Float, nullable=False)
    longitude = db.Column(db.Float, nullable=False)
    temperature = db.Column(db.Float, nullable=False)
    humidity = db.Column(db.Integer, nullable=False)
    wind_speed = db.Column(db.Float, nullable=False)
    precipitation = db.Column(db.Float, nullable=True)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)


class MapSuggestion(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    suggestion_type = db.Column(db.String(50), nullable=False)  # street, building, business
    name = db.Column(db.String(200), nullable=False)
    latitude = db.Column(db.Float, nullable=False)
    longitude = db.Column(db.Float, nullable=False)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
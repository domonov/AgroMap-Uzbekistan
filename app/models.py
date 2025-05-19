from datetime import datetime
from app import db, login
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
import json

class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(64), index=True, unique=True)
    email = db.Column(db.String(120), index=True, unique=True)
    password_hash = db.Column(db.String(128))
    role = db.Column(db.String(20), default='user')
    fields = db.relationship('Field', backref='owner', lazy='dynamic')
    reports = db.relationship('Report', backref='author', lazy='dynamic')
    
    def __repr__(self):
        return f'<User {self.username}>'
    
    def set_password(self, password):
        self.password_hash = generate_password_hash(password)
        
    def check_password(self, password):
        return check_password_hash(self.password_hash, password)
    
    def to_dict(self):
        return {
            'id': self.id,
            'username': self.username,
            'email': self.email,
            'role': self.role
        }

@login.user_loader
def load_user(id):
    return User.query.get(int(id))

class Crop(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(64), index=True)
    description = db.Column(db.String(256))
    growing_season = db.Column(db.String(64))
    water_requirements = db.Column(db.String(64))
    fields = db.relationship('Field', backref='crop', lazy='dynamic')
    
    def __repr__(self):
        return f'<Crop {self.name}>'
    
    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'description': self.description,
            'growing_season': self.growing_season,
            'water_requirements': self.water_requirements
        }

class Field(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(64))
    location = db.Column(db.String(128))
    area = db.Column(db.Float)
    geometry = db.Column(db.Text)  # GeoJSON string
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    crop_id = db.Column(db.Integer, db.ForeignKey('crop.id'))
    planting_date = db.Column(db.DateTime)
    harvest_date = db.Column(db.DateTime)
    
    def __repr__(self):
        return f'<Field {self.name}>'
    
    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'location': self.location,
            'area': self.area,
            'geometry': json.loads(self.geometry) if self.geometry else None,
            'user_id': self.user_id,
            'crop_id': self.crop_id,
            'crop_name': self.crop.name if self.crop else None,
            'planting_date': self.planting_date.strftime('%Y-%m-%d') if self.planting_date else None,
            'harvest_date': self.harvest_date.strftime('%Y-%m-%d') if self.harvest_date else None
        }

class WeatherData(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    location = db.Column(db.String(128))
    timestamp = db.Column(db.DateTime, index=True, default=datetime.utcnow)
    temperature = db.Column(db.Float)
    humidity = db.Column(db.Float)
    precipitation = db.Column(db.Float)
    wind_speed = db.Column(db.Float)
    forecast = db.Column(db.Text)  # JSON string for forecast data
    
    def __repr__(self):
        return f'<Weather {self.location} at {self.timestamp}>'
    
    def to_dict(self):
        return {
            'id': self.id,
            'location': self.location,
            'timestamp': self.timestamp.strftime('%Y-%m-%d %H:%M:%S'),
            'temperature': self.temperature,
            'humidity': self.humidity,
            'precipitation': self.precipitation,
            'wind_speed': self.wind_speed,
            'forecast': json.loads(self.forecast) if self.forecast else None
        }

class Report(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(128))
    content = db.Column(db.Text)
    location = db.Column(db.String(128))
    timestamp = db.Column(db.DateTime, index=True, default=datetime.utcnow)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    
    def __repr__(self):
        return f'<Report {self.title}>'
    
    def to_dict(self):
        return {
            'id': self.id,
            'title': self.title,
            'content': self.content,
            'location': self.location,
            'timestamp': self.timestamp.strftime('%Y-%m-%d %H:%M:%S'),
            'user_id': self.user_id,
            'author': self.author.username
        }

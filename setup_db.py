from app import app, db
from app.models import User, Crop, Field, WeatherData, Report
from datetime import datetime, timedelta
import json

def setup_database():
    # Create all tables
    with app.app_context():
        db.create_all()
        
        # Check if there's already data in the database
        if User.query.first() is not None:
            print("Database already contains data. Skipping initialization.")
            return
        
        # Create admin user
        admin = User(username='admin', email='admin@agromap.uz', role='admin')
        admin.set_password('admin123')
        db.session.add(admin)
        
        # Create regular user
        user = User(username='testuser', email='user@agromap.uz', role='user')
        user.set_password('password123')
        db.session.add(user)
        
        # Create crops
        crops = [
            Crop(name='Cotton', description='Primary cash crop in Uzbekistan', 
                 growing_season='April-October', water_requirements='High'),
            Crop(name='Wheat', description='Major winter grain crop', 
                 growing_season='October-June', water_requirements='Medium'),
            Crop(name='Rice', description='Grown in irrigated areas', 
                 growing_season='May-September', water_requirements='Very High'),
            Crop(name='Fruit', description='Various fruits including apples, grapes, melons', 
                 growing_season='March-October', water_requirements='Medium-High'),
            Crop(name='Vegetables', description='Various vegetables for local consumption', 
                 growing_season='March-October', water_requirements='Medium')
        ]
        for crop in crops:
            db.session.add(crop)
        
        # Add some sample weather data
        locations = ['Tashkent', 'Samarkand', 'Bukhara', 'Fergana Valley', 'Karakalpakstan']
        
        for i, location in enumerate(locations):
            # Current weather
            current = WeatherData(
                location=location,
                temperature=25 + i,
                humidity=40 - i*2,
                precipitation=0,
                wind_speed=5 + i/2,
                timestamp=datetime.now(),
                forecast=json.dumps([{
                    'date': (datetime.now() + timedelta(days=day)).strftime('%Y-%m-%d'),
                    'temp_max': 25 + i + day,
                    'temp_min': 15 + i,
                    'description': 'Sunny'
                } for day in range(1, 8)])
            )
            db.session.add(current)
            
            # Add some historical weather data
            for day in range(1, 10):
                hist = WeatherData(
                    location=location,
                    temperature=25 + i - day/2,
                    humidity=40 - i*2 + day,
                    precipitation=day % 3,
                    wind_speed=5 + i/2 - day/4,
                    timestamp=datetime.now() - timedelta(days=day)
                )
                db.session.add(hist)
        
        # Create sample fields for test user
        field_geometries = [
            # Simple polygon for a cotton field
            {
                "type": "Polygon",
                "coordinates": [[[64.5, 41.3], [64.51, 41.3], [64.51, 41.31], [64.5, 41.31], [64.5, 41.3]]]
            },
            # Simple polygon for a wheat field
            {
                "type": "Polygon",
                "coordinates": [[[64.53, 41.32], [64.54, 41.32], [64.54, 41.33], [64.53, 41.33], [64.53, 41.32]]]
            }
        ]
        
        fields = [
            Field(
                name='Cotton Field 1',
                location='Tashkent Region',
                area=15.6,
                geometry=json.dumps(field_geometries[0]),
                user_id=2,  # test user
                crop_id=1,  # Cotton
                planting_date=datetime.strptime('2025-04-15', '%Y-%m-%d'),
                harvest_date=datetime.strptime('2025-10-01', '%Y-%m-%d')
            ),
            Field(
                name='Wheat Field 1',
                location='Samarkand Region',
                area=20.3,
                geometry=json.dumps(field_geometries[1]),
                user_id=2,  # test user
                crop_id=2,  # Wheat
                planting_date=datetime.strptime('2024-10-10', '%Y-%m-%d'),
                harvest_date=datetime.strptime('2025-06-15', '%Y-%m-%d')
            )
        ]
        
        for field in fields:
            db.session.add(field)
        
        # Create sample reports
        reports = [
            Report(
                title='Drought Conditions in Karakalpakstan',
                content='Prolonged drought is affecting crop development. Irrigation systems need maintenance.',
                location='Karakalpakstan',
                user_id=2,  # test user
                timestamp=datetime.now() - timedelta(days=5)
            ),
            Report(
                title='Excellent Wheat Growth in Samarkand',
                content='The wheat crop is developing well with recent rainfall.',
                location='Samarkand Region',
                user_id=2,  # test user
                timestamp=datetime.now() - timedelta(days=2)
            )
        ]
        
        for report in reports:
            db.session.add(report)
            
        # Commit all changes
        db.session.commit()
        print("Database initialized with sample data.")

if __name__ == '__main__':
    setup_database()

# AgroMap Uzbekistan 🌍🌱  
A community-driven web app for smarter crop planning and better mapping of Uzbekistan's agricultural landscape.

## 🚀 Project Overview
Agriculture accounts for **1/5 of Uzbekistan's annual GDP**, yet farmers often make planting decisions **based on habit or past prices**, leading to oversupply of some crops and shortages of others.  

🚜 **AgroMap Uzbekistan** aims to **help farmers make informed planting decisions** using a **publicly sourced mapping system**. The app visualizes crop planting trends, predicts market prices, and allows users to **suggest map improvements** like street names and business locations.

## ✨ Key Features

### 🗺️ Interactive Regional Map
- **Auto-location**: Automatically detects user's approximate location via IP geolocation
- **Multiple map layers**: Street view, satellite imagery, and terrain maps
- **Mobile-first design**: Optimized for smartphones and tablets
- **Real-time crop visualization**: Heat maps showing crop distribution by region

### 🌾 Crop Planning & Reporting
- **Simple data input**: Just crop type and field size required
- **Visual crop markers**: Different icons for wheat, cotton, potato, and more
- **Field boundary drawing**: Option to draw actual field shapes on the map
- **Planting date tracking**: When crops were/will be planted
- **Edit and delete**: Manage your own crop reports

### 📊 Trends & Price Prediction
- **Crop distribution analytics**: See what's being planted in your area
- **Price prediction system**: ML-powered price forecasts for major crops
- **Historical trends**: Monthly planting patterns and market data
- **Market confidence indicators**: How reliable the predictions are

### 🗺️ Crowdsourced Map Improvements
- **Street name suggestions**: Help add missing street names
- **Building addresses**: Suggest building numbers and names
- **Business locations**: Add shops, markets, and agricultural services
- **Community-driven**: The more users contribute, the better the maps become

### 🌐 Multi-language Support
- **Uzbek (O'zbek)**: Native language support
- **Russian (Русский)**: Widely spoken secondary language
- **English**: International accessibility
- **Easy language switching**: One-click language change

## 🔥 Getting Started

### Prerequisites
- Python 3.8 or higher
- pip (Python package manager)
- Modern web browser with JavaScript enabled

### Installation & Setup

1. **Clone the repository**
   ```bash
   git clone https://github.com/yourusername/AgroMap-Uzbekistan.git
   cd AgroMap-Uzbekistan
   ```

2. **Create a virtual environment**
   ```bash
   python -m venv venv
   
   # On Windows:
   venv\Scripts\activate
   
   # On macOS/Linux:
   source venv/bin/activate
   ```

3. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

4. **Set up environment variables** (optional)
   Create a `.env` file in the root directory:
   ```env
   FLASK_SECRET_KEY=your-secret-key-here
   DEFAULT_LANGUAGE=en
   DATABASE_URL=sqlite:///agromap.db
   ```

5. **Initialize the database**
   ```bash
   python run.py
   ```
   The database will be automatically created on first run.

6. **Run the application**
   ```bash
   python run.py
   ```

7. **Open your browser**
   Navigate to `http://localhost:5000`

## 🏗️ Project Structure

```
AgroMap-Uzbekistan/
├── app/
│   ├── __init__.py           # Flask app factory
│   ├── routes.py             # API endpoints and routes
│   ├── models.py             # Database models
│   ├── services/             # Business logic
│   │   ├── crop_advisor.py   # Crop rotation and timing advice
│   │   ├── weather_service.py # Weather data integration
│   │   └── yield_predictor.py # Price and yield predictions
│   ├── static/               # Frontend assets
│   │   ├── css/style.css     # Main stylesheet
│   │   ├── js/main.js        # Frontend JavaScript
│   │   └── images/           # Icons and images
│   ├── templates/            # HTML templates
│   │   └── index.html        # Main application page
│   └── translations/         # Multi-language support
├── docs/                     # Documentation
├── requirements.txt          # Python dependencies
├── run.py                    # Application entry point
└── README.md                 # This file
```

## 🛠️ Technology Stack

### Backend
- **Flask**: Lightweight Python web framework
- **SQLAlchemy**: Database ORM for data management
- **Flask-Migrate**: Database migration management
- **Requests**: HTTP client for external API calls

### Frontend
- **Leaflet.js**: Interactive mapping library
- **OpenStreetMap**: Free map tiles and data
- **Vanilla JavaScript**: No heavy frameworks, fast loading
- **Responsive CSS**: Mobile-first design approach

### Database
- **SQLite**: Development database (default)
- **PostgreSQL**: Production database (recommended)
- **PostGIS support**: For advanced geospatial queries

## 📱 API Endpoints

### Crop Reports
- `GET /api/crop-reports` - Retrieve all crop reports
- `POST /api/crop-reports` - Submit new crop report
- `PUT /api/crop-reports` - Update existing report
- `DELETE /api/crop-reports?id=<id>` - Delete report

### Analytics & Trends
- `GET /api/crop-trends` - Get aggregated crop statistics
- `GET /api/price-prediction/<crop_type>` - Get price forecast
- `GET /api/crop-advisor` - Get planting time recommendations

### Map Features
- `GET /api/map-suggestions` - Retrieve map improvement suggestions
- `POST /api/map-suggestions` - Submit new map suggestion
- `GET /api/location-from-ip` - Get approximate location from IP
- `GET /api/weather` - Current weather data

### Utilities
- `GET /set-language/<language>` - Change interface language

## 🚀 Deployment

### Development
```bash
python run.py
```

### Production (Heroku)
1. Install Heroku CLI
2. Create Heroku app: `heroku create your-app-name`
3. Add PostgreSQL: `heroku addons:create heroku-postgresql:hobby-dev`
4. Deploy: `git push heroku main`

### Production (Traditional Server)
1. Install Gunicorn: `pip install gunicorn`
2. Run with: `gunicorn -w 4 -b 0.0.0.0:8000 run:app`
3. Use nginx as reverse proxy
4. Set up SSL certificate

## 🤝 Contributing

We welcome contributions! Here's how you can help:

1. **Report bugs**: Open an issue with detailed description
2. **Suggest features**: Propose new functionality
3. **Submit code**: Fork, create branch, make changes, submit PR
4. **Improve docs**: Help make documentation clearer
5. **Test the app**: Use it and provide feedback

### Development Guidelines
- Follow PEP 8 for Python code
- Use meaningful commit messages
- Test your changes thoroughly
- Update documentation for new features

## 📊 Roadmap

### Phase 1 (Current) - MVP
- ✅ Basic map interface with crop reporting
- ✅ Multi-language support
- ✅ Crop trends and statistics
- ✅ Map improvement suggestions

### Phase 2 - Enhanced Analytics
- 🔄 Machine learning price prediction
- 🔄 Weather integration
- 🔄 Advanced crop rotation advice
- 🔄 Government dashboard

### Phase 3 - Advanced Features
- 📅 Mobile app development
- 📅 Farmer social network
- 📅 Marketplace integration
- 📅 Drone imagery analysis

## 🌟 Impact Goals

- **Reduce crop waste** by 20% through better planning
- **Increase farmer income** via informed decision making
- **Improve food security** through supply prediction
- **Enhance map accuracy** for rural Uzbekistan
- **Support government** agricultural policy decisions

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 📞 Support

- **Documentation**: Check the `/docs` folder
- **Issues**: Open a GitHub issue
- **Discussions**: Use GitHub Discussions
- **Email**: contact@agromap-uzbekistan.org

## 🙏 Acknowledgments

- OpenStreetMap contributors for map data
- Uzbekistan farming communities for inspiration
- Flask and Leaflet.js communities for excellent tools
- All contributors and beta testers

---

**Made with ❤️ for Uzbekistan's farmers** 🇺🇿
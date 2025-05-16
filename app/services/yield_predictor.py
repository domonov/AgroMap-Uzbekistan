from datetime import datetime

class YieldPredictor:
    def __init__(self):
        # Base yields in tons per hectare for different crops
        self.base_yields = {
            'wheat': 3.5,
            'cotton': 2.8,
            'potato': 25.0
        }
        
        # Optimal planting months for each crop
        self.optimal_months = {
            'wheat': [9, 10, 11],    # September to November
            'cotton': [3, 4],        # March to April
            'potato': [2, 3]         # February to March
        }

    # Enhance your YieldPredictor class
    def predict(self, report_data, weather_data=None):
        """
        Predict yield based on simple rules and historical averages
        """
        try:
            crop_type = report_data.get('crop_type')
            field_size = float(report_data.get('field_size', 0))
            planting_date = datetime.strptime(report_data.get('planting_date', ''), '%Y-%m-%d')
            
            if not all([crop_type, field_size, planting_date]):
                return None

            # Get base yield for crop type
            base_yield = self.base_yields.get(crop_type, 0)
            
            # Apply seasonal adjustment
            month = planting_date.month
            seasonal_factor = 1.0 if month in self.optimal_months.get(crop_type, []) else 0.8
            
            # Apply weather factor if available
            weather_factor = 1.0
            if weather_data:
                # Adjust based on temperature and precipitation
                avg_temp = sum(w['temperature'] for w in weather_data) / len(weather_data)
                total_rain = sum(w.get('precipitation', 0) for w in weather_data)
                
                # Simple weather adjustment logic
                if 15 <= avg_temp <= 25:  # Optimal temperature range
                    weather_factor *= 1.1
                
                if crop_type == 'wheat' and 300 <= total_rain <= 500:
                    weather_factor *= 1.1
            
            # Final prediction with weather factor
            predicted_yield = base_yield * seasonal_factor * weather_factor * field_size
            
            return {
                'predicted_yield': round(predicted_yield, 2),
                'confidence': 0.7,  # Fixed confidence level
                'optimal_planting': month in self.optimal_months.get(crop_type, [])
            }
            
        except Exception as e:
            print(f"Prediction error: {e}")
            return None
from datetime import datetime
import math

class YieldPredictor:
    def __init__(self):
        # Base yields in tons per hectare for different crops
        self.base_yields = {
            'wheat': 3.5,
            'cotton': 2.8,
            'potato': 25.0,
            'rice': 4.2,
            'corn': 6.8
        }
        
        # Optimal planting months for each crop
        self.optimal_months = {
            'wheat': [9, 10, 11],    # September to November
            'cotton': [3, 4],        # March to April
            'potato': [2, 3],        # February to March
            'rice': [4, 5],          # April to May
            'corn': [4, 5, 6]        # April to June
        }
        
        # Crop-specific environmental requirements
        self.crop_requirements = {
            'wheat': {
                'optimal_temp_range': (15, 25),
                'optimal_rainfall': (400, 600),
                'soil_ph_range': (6.0, 7.5),
                'drought_tolerance': 0.7
            },
            'cotton': {
                'optimal_temp_range': (20, 30),
                'optimal_rainfall': (500, 800),
                'soil_ph_range': (5.5, 8.0),
                'drought_tolerance': 0.8
            },
            'potato': {
                'optimal_temp_range': (10, 20),
                'optimal_rainfall': (400, 500),
                'soil_ph_range': (4.5, 6.5),
                'drought_tolerance': 0.4
            },
            'rice': {
                'optimal_temp_range': (25, 35),
                'optimal_rainfall': (1000, 1500),
                'soil_ph_range': (5.5, 6.5),
                'drought_tolerance': 0.2
            },            'corn': {
                'optimal_temp_range': (18, 27),
                'optimal_rainfall': (500, 750),
                'soil_ph_range': (6.0, 7.0),
                'drought_tolerance': 0.6
            }
        }

    def predict(self, report_data, weather_data=None, soil_data=None):
        """
        Advanced yield prediction using multiple factors
        """
        try:
            crop_type = report_data.get('crop_type')
            field_size = float(report_data.get('field_size', 0))
            planting_date = datetime.strptime(report_data.get('planting_date', ''), '%Y-%m-%d')
            
            if not all([crop_type, field_size, planting_date]):
                return None

            # Get base yield for crop type
            base_yield = self.base_yields.get(crop_type, 0)
            
            # Calculate multiple adjustment factors
            seasonal_factor = self._calculate_seasonal_factor(crop_type, planting_date)
            weather_factor = self._calculate_weather_factor(crop_type, weather_data)
            soil_factor = self._calculate_soil_factor(crop_type, soil_data)
            field_size_factor = self._calculate_field_size_factor(field_size)
            
            # Apply ML-inspired weighting
            adjusted_yield = base_yield * seasonal_factor * weather_factor * soil_factor * field_size_factor
            
            # Calculate total expected yield
            total_yield = adjusted_yield * field_size
            
            # Generate confidence score
            confidence = self._calculate_confidence(weather_data, soil_data)
            
            return {
                'yield_per_hectare': round(adjusted_yield, 2),
                'total_yield': round(total_yield, 2),
                'confidence': confidence,
                'factors': {
                    'seasonal': seasonal_factor,
                    'weather': weather_factor,
                    'soil': soil_factor,
                    'field_size': field_size_factor
                },
                'recommendations': self._generate_recommendations(crop_type, weather_data, soil_data)
            }
            
        except Exception as e:
            return None
    
    def _calculate_seasonal_factor(self, crop_type, planting_date):
        """Calculate seasonal planting factor"""
        month = planting_date.month
        optimal_months = self.optimal_months.get(crop_type, [])
        
        if month in optimal_months:
            return 1.0
        
        # Calculate distance from optimal planting window
        if optimal_months:
            min_distance = min(abs(month - opt_month) for opt_month in optimal_months)
            # Exponential decay for seasonal timing
            return max(0.6, math.exp(-min_distance * 0.3))
        
        return 0.8
    
    def _calculate_weather_factor(self, crop_type, weather_data):
        """Calculate weather impact factor"""
        if not weather_data:
            return 1.0
        
        requirements = self.crop_requirements.get(crop_type, {})
        
        # Average temperature analysis
        temps = [w.get('temperature', 20) for w in weather_data]
        avg_temp = sum(temps) / len(temps) if temps else 20
        
        temp_range = requirements.get('optimal_temp_range', (15, 25))
        temp_factor = self._gaussian_factor(avg_temp, temp_range)
        
        # Rainfall analysis
        total_rainfall = sum(w.get('precipitation', 0) for w in weather_data)
        rainfall_range = requirements.get('optimal_rainfall', (400, 600))
        rainfall_factor = self._gaussian_factor(total_rainfall, rainfall_range)
        
        # Combine factors with weights
        return (temp_factor * 0.6 + rainfall_factor * 0.4)
    
    def _calculate_soil_factor(self, crop_type, soil_data):
        """Calculate soil quality factor"""
        if not soil_data:
            return 1.0
        
        requirements = self.crop_requirements.get(crop_type, {})
        
        # pH analysis
        soil_ph = soil_data.get('ph', 6.5)
        ph_range = requirements.get('soil_ph_range', (6.0, 7.0))
        ph_factor = self._gaussian_factor(soil_ph, ph_range)
        
        # Organic matter content
        organic_matter = soil_data.get('organic_matter', 2.5)
        organic_factor = min(1.2, organic_matter / 3.0)  # Cap at 1.2x boost
        
        # Nutrient availability
        nutrients = soil_data.get('nutrients', {})
        nutrient_factor = self._calculate_nutrient_factor(nutrients)
        
        return (ph_factor * 0.4 + organic_factor * 0.3 + nutrient_factor * 0.3)
    
    def _calculate_field_size_factor(self, field_size):
        """Calculate field size efficiency factor"""
        # Economies of scale for larger fields, diminishing returns
        if field_size <= 1:
            return 0.9  # Small fields are less efficient
        elif field_size <= 5:
            return 1.0
        elif field_size <= 20:
            return 1.1  # Optimal size range
        else:
            return 1.05  # Large fields have marginal benefits
    
    def _gaussian_factor(self, value, optimal_range):
        """Calculate factor using Gaussian distribution around optimal range"""
        optimal_center = (optimal_range[0] + optimal_range[1]) / 2
        optimal_width = (optimal_range[1] - optimal_range[0]) / 4  # Standard deviation
        
        # Gaussian function
        exponent = -((value - optimal_center) ** 2) / (2 * optimal_width ** 2)
        return max(0.5, math.exp(exponent))
    
    def _calculate_nutrient_factor(self, nutrients):
        """Calculate nutrient availability factor"""
        if not nutrients:
            return 1.0
        
        # Primary nutrients (N-P-K)
        nitrogen = nutrients.get('nitrogen', 50)
        phosphorus = nutrients.get('phosphorus', 25)
        potassium = nutrients.get('potassium', 150)
        
        # Simple nutrient scoring (0-100 scale)
        n_factor = min(1.2, nitrogen / 60.0)
        p_factor = min(1.2, phosphorus / 30.0)
        k_factor = min(1.2, potassium / 180.0)
        
        return (n_factor + p_factor + k_factor) / 3
    
    def _calculate_confidence(self, weather_data, soil_data):
        """Calculate prediction confidence score"""
        confidence = 0.5  # Base confidence
        
        if weather_data:
            confidence += 0.3
        if soil_data:
            confidence += 0.2
        
        return min(0.95, confidence)
    
    def _generate_recommendations(self, crop_type, weather_data, soil_data):
        """Generate actionable recommendations"""
        recommendations = []
        
        requirements = self.crop_requirements.get(crop_type, {})
        
        if weather_data:
            avg_temp = sum(w.get('temperature', 20) for w in weather_data) / len(weather_data)
            temp_range = requirements.get('optimal_temp_range', (15, 25))
            
            if avg_temp < temp_range[0]:
                recommendations.append("Consider using row covers or greenhouse protection for temperature control")
            elif avg_temp > temp_range[1]:
                recommendations.append("Implement shade structures or cooling systems during hot periods")
            
            total_rainfall = sum(w.get('precipitation', 0) for w in weather_data)
            rainfall_range = requirements.get('optimal_rainfall', (400, 600))
            
            if total_rainfall < rainfall_range[0]:
                recommendations.append("Increase irrigation frequency to compensate for low rainfall")
            elif total_rainfall > rainfall_range[1]:
                recommendations.append("Ensure proper drainage to prevent waterlogging")
        
        if soil_data:
            soil_ph = soil_data.get('ph', 6.5)
            ph_range = requirements.get('soil_ph_range', (6.0, 7.0))
            
            if soil_ph < ph_range[0]:
                recommendations.append("Apply lime to increase soil pH")
            elif soil_ph > ph_range[1]:
                recommendations.append("Apply sulfur or organic matter to lower soil pH")
          # Generic recommendations
        recommendations.append(f"Monitor for pests and diseases common to {crop_type}")
        recommendations.append("Follow integrated pest management practices")
        
        return recommendations
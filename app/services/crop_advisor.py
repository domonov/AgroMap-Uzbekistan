from datetime import datetime
import math

class CropAdvisor:
    def __init__(self):
        # Enhanced rotation rules with sustainability scoring
        self.rotation_rules = {
            'wheat': [
                {'crop': 'cotton', 'benefit_score': 0.8, 'nitrogen_benefit': True},
                {'crop': 'potato', 'benefit_score': 0.7, 'nitrogen_benefit': False},
                {'crop': 'corn', 'benefit_score': 0.6, 'nitrogen_benefit': False}
            ],
            'cotton': [
                {'crop': 'wheat', 'benefit_score': 0.9, 'nitrogen_benefit': True},
                {'crop': 'potato', 'benefit_score': 0.7, 'nitrogen_benefit': False}
            ],
            'potato': [
                {'crop': 'wheat', 'benefit_score': 0.8, 'nitrogen_benefit': True},
                {'crop': 'cotton', 'benefit_score': 0.6, 'nitrogen_benefit': False}
            ],
            'rice': [
                {'crop': 'wheat', 'benefit_score': 0.7, 'nitrogen_benefit': True},
                {'crop': 'corn', 'benefit_score': 0.8, 'nitrogen_benefit': False}
            ],
            'corn': [
                {'crop': 'wheat', 'benefit_score': 0.8, 'nitrogen_benefit': True},
                {'crop': 'potato', 'benefit_score': 0.7, 'nitrogen_benefit': False}
            ]
        }
        
        # Market demand factors (0-1 scale)
        self.market_demand = {
            'wheat': 0.9,
            'cotton': 0.8,
            'potato': 0.7,
            'rice': 0.8,
            'corn': 0.7
        }
        
        # Environmental adaptability scores
        self.climate_adaptability = {
            'wheat': {'drought_tolerance': 0.7, 'heat_tolerance': 0.6, 'cold_tolerance': 0.8},
            'cotton': {'drought_tolerance': 0.8, 'heat_tolerance': 0.9, 'cold_tolerance': 0.3},
            'potato': {'drought_tolerance': 0.4, 'heat_tolerance': 0.5, 'cold_tolerance': 0.7},
            'rice': {'drought_tolerance': 0.2, 'heat_tolerance': 0.8, 'cold_tolerance': 0.4},
            'corn': {'drought_tolerance': 0.6, 'heat_tolerance': 0.7, 'cold_tolerance': 0.5}
        }
          # Enhanced planting calendar with climate zones
        self.planting_calendar = {
            'wheat': {'start_month': 9, 'end_month': 11, 'growth_days': 180},
            'cotton': {'start_month': 3, 'end_month': 5, 'growth_days': 200},
            'potato': {'start_month': 2, 'end_month': 4, 'growth_days': 120},
            'rice': {'start_month': 4, 'end_month': 6, 'growth_days': 150},
            'corn': {'start_month': 4, 'end_month': 6, 'growth_days': 140}
        }

    def get_smart_recommendations(self, location_data, weather_data=None, soil_data=None, previous_crops=None):
        """Get intelligent crop recommendations using ML-inspired algorithms"""
        recommendations = []
        
        for crop in self.planting_calendar.keys():
            score = self._calculate_crop_suitability_score(
                crop, location_data, weather_data, soil_data, previous_crops
            )
            
            recommendations.append({
                'crop': crop,
                'suitability_score': round(score, 2),
                'planting_info': self.get_planting_time(crop),
                'rotation_benefit': self._get_rotation_benefit(crop, previous_crops),
                'environmental_factors': self._analyze_environmental_factors(crop, weather_data),
                'market_potential': self.market_demand.get(crop, 0.5)
            })
        
        # Sort by suitability score
        recommendations.sort(key=lambda x: x['suitability_score'], reverse=True)
        
        return recommendations[:5]  # Return top 5 recommendations
    
    def _calculate_crop_suitability_score(self, crop, location_data, weather_data, soil_data, previous_crops):
        """Calculate overall suitability score for a crop"""
        score = 0.5  # Base score
        
        # Seasonal timing factor (30% weight)
        seasonal_score = self._calculate_seasonal_score(crop)
        score += seasonal_score * 0.3
        
        # Climate adaptation factor (25% weight)
        climate_score = self._calculate_climate_score(crop, weather_data)
        score += climate_score * 0.25
        
        # Soil suitability factor (20% weight)
        soil_score = self._calculate_soil_score(crop, soil_data)
        score += soil_score * 0.2
        
        # Rotation benefit factor (15% weight)
        rotation_score = self._calculate_rotation_score(crop, previous_crops)
        score += rotation_score * 0.15
        
        # Market demand factor (10% weight)
        market_score = self.market_demand.get(crop, 0.5)
        score += market_score * 0.1
        
        return min(1.0, score)
    
    def _calculate_seasonal_score(self, crop):
        """Calculate seasonal planting score"""
        calendar = self.planting_calendar.get(crop, {})
        if not calendar:
            return 0.5
        
        current_month = datetime.now().month
        start_month = calendar['start_month']
        end_month = calendar['end_month']
        
        # Check if in optimal planting window
        if self._is_month_in_range(current_month, start_month, end_month):
            return 1.0
        
        # Calculate distance from optimal window
        distance = self._calculate_month_distance(current_month, start_month, end_month)
        
        # Exponential decay based on distance
        return max(0.2, math.exp(-distance * 0.5))
    
    def _calculate_climate_score(self, crop, weather_data):
        """Calculate climate adaptation score"""
        if not weather_data:
            return 0.7  # Default moderate score
        
        adaptability = self.climate_adaptability.get(crop, {})
        score = 0.7  # Base score
        
        # Analyze temperature extremes
        temperatures = [w.get('temperature', 20) for w in weather_data]
        avg_temp = sum(temperatures) / len(temperatures)
        max_temp = max(temperatures)
        min_temp = min(temperatures)
        
        # Heat tolerance assessment
        if max_temp > 30:
            heat_factor = adaptability.get('heat_tolerance', 0.5)
            score *= (0.5 + heat_factor * 0.5)
        
        # Cold tolerance assessment
        if min_temp < 5:
            cold_factor = adaptability.get('cold_tolerance', 0.5)
            score *= (0.5 + cold_factor * 0.5)
        
        # Drought tolerance assessment
        total_rainfall = sum(w.get('precipitation', 0) for w in weather_data)
        if total_rainfall < 300:  # Low rainfall threshold
            drought_factor = adaptability.get('drought_tolerance', 0.5)
            score *= (0.5 + drought_factor * 0.5)
        
        return min(1.0, score)
    
    def _calculate_soil_score(self, crop, soil_data):
        """Calculate soil suitability score"""
        if not soil_data:
            return 0.7  # Default moderate score
        
        # Crop-specific soil requirements
        soil_requirements = {
            'wheat': {'ph_range': (6.0, 7.5), 'drainage': 'good'},
            'cotton': {'ph_range': (5.5, 8.0), 'drainage': 'good'},
            'potato': {'ph_range': (4.5, 6.5), 'drainage': 'excellent'},
            'rice': {'ph_range': (5.5, 6.5), 'drainage': 'poor'},
            'corn': {'ph_range': (6.0, 7.0), 'drainage': 'good'}
        }
        
        requirements = soil_requirements.get(crop, {})
        score = 0.7
        
        # pH suitability
        soil_ph = soil_data.get('ph', 6.5)
        ph_range = requirements.get('ph_range', (6.0, 7.0))
        
        if ph_range[0] <= soil_ph <= ph_range[1]:
            score += 0.2
        else:
            ph_distance = min(abs(soil_ph - ph_range[0]), abs(soil_ph - ph_range[1]))
            score += max(0, 0.2 - ph_distance * 0.1)
        
        # Organic matter content
        organic_matter = soil_data.get('organic_matter', 2.0)
        if organic_matter > 3.0:
            score += 0.1
        
        return min(1.0, score)
    
    def _calculate_rotation_score(self, crop, previous_crops):
        """Calculate crop rotation benefit score"""
        if not previous_crops:
            return 0.7
        
        last_crop = previous_crops[-1] if previous_crops else None
        
        if last_crop == crop:
            return 0.2  # Penalty for monoculture
        
        rotation_options = self.rotation_rules.get(last_crop, [])
        for option in rotation_options:
            if option['crop'] == crop:
                return option['benefit_score']
        
        return 0.6  # Neutral score for unspecified rotations
    
    def _get_rotation_benefit(self, crop, previous_crops):
        """Get detailed rotation benefit information"""
        if not previous_crops:
            return "No previous crop data available"
        
        last_crop = previous_crops[-1]
        
        if last_crop == crop:
            return "⚠️ Monoculture risk - consider rotation"
        
        rotation_options = self.rotation_rules.get(last_crop, [])
        for option in rotation_options:
            if option['crop'] == crop:
                benefits = ["✓ Good rotation choice"]
                if option.get('nitrogen_benefit'):
                    benefits.append("✓ Nitrogen fixation benefit")
                return " | ".join(benefits)
        
        return "Neutral rotation effect"
    
    def _analyze_environmental_factors(self, crop, weather_data):
        """Analyze environmental risk factors"""
        factors = []
        
        if not weather_data:
            return ["Insufficient weather data for analysis"]
        
        adaptability = self.climate_adaptability.get(crop, {})
        
        # Temperature analysis
        temperatures = [w.get('temperature', 20) for w in weather_data]
        max_temp = max(temperatures)
        min_temp = min(temperatures)
        
        if max_temp > 35 and adaptability.get('heat_tolerance', 0.5) < 0.6:
            factors.append("🌡️ Heat stress risk")
        
        if min_temp < 0 and adaptability.get('cold_tolerance', 0.5) < 0.6:
            factors.append("❄️ Frost risk")
        
        # Precipitation analysis
        total_rainfall = sum(w.get('precipitation', 0) for w in weather_data)
        if total_rainfall < 200 and adaptability.get('drought_tolerance', 0.5) < 0.6:
            factors.append("💧 Drought stress risk")
        
        if total_rainfall > 1000 and crop != 'rice':
            factors.append("🌊 Waterlogging risk")
        
        return factors if factors else ["✓ Favorable environmental conditions"]
    
    def _is_month_in_range(self, month, start_month, end_month):
        """Check if month is in planting range, handling year boundaries"""
        if start_month <= end_month:
            return start_month <= month <= end_month
        else:
            return month >= start_month or month <= end_month
    
    def _calculate_month_distance(self, current_month, start_month, end_month):
        """Calculate minimum distance to planting window"""
        if self._is_month_in_range(current_month, start_month, end_month):
            return 0
        
        # Calculate distances to start and end of window
        if start_month <= end_month:
            dist_to_start = min(abs(current_month - start_month), 
                              12 - abs(current_month - start_month))
            dist_to_end = min(abs(current_month - end_month),
                            12 - abs(current_month - end_month))
        else:
            # Handle year boundary
            if current_month > end_month and current_month < start_month:
                dist_to_start = start_month - current_month
                dist_to_end = current_month - end_month
            else:
                dist_to_start = 0
                dist_to_end = 0
        
        return min(dist_to_start, dist_to_end)
    
    def get_planting_time(self, crop_type):
        """Get optimal planting time for a crop"""
        if crop_type not in self.planting_calendar:
            return None
        
        calendar = self.planting_calendar[crop_type]
        
        # Convert month numbers to names
        months = ['January', 'February', 'March', 'April', 'May', 'June',
                 'July', 'August', 'September', 'October', 'November', 'December']
                 
        start_month = months[calendar['start_month'] - 1]
        end_month = months[calendar['end_month'] - 1]
        
        return {
            'start_month': start_month,
            'end_month': end_month,
            'is_optimal_now': self._is_optimal_now(calendar)
        }
    
    def _is_optimal_now(self, calendar):
        """Check if current month is optimal for planting"""
        from datetime import datetime
        current_month = datetime.now().month
        
        # Handle year wrap (e.g., Nov-Feb spans year boundary)
        if calendar['start_month'] > calendar['end_month']:
            return current_month >= calendar['start_month'] or current_month <= calendar['end_month']
        else:
            return calendar['start_month'] <= current_month <= calendar['end_month']
    
    def get_rotation_suggestions(self, previous_crop):
        """Get crop rotation suggestions based on previous crop"""
        if not previous_crop:
            return [opt['crop'] for opts in self.rotation_rules.values() for opt in opts]
        
        rotation_options = self.rotation_rules.get(previous_crop, [])
        return [opt['crop'] for opt in rotation_options]
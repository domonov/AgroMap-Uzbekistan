"""
Advanced Crop Rotation Planning Service for AgroMap Uzbekistan
Provides multi-season planning, rotation optimization, and agricultural best practices
"""

import sqlite3
import json
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Tuple
import logging
from dataclasses import dataclass
from enum import Enum

logger = logging.getLogger(__name__)

class SeasonType(Enum):
    SPRING = "spring"
    SUMMER = "summer"
    AUTUMN = "autumn"
    WINTER = "winter"

@dataclass
class CropCompatibility:
    crop_type: str
    nitrogen_requirement: str  # low, medium, high
    nitrogen_production: str   # none, low, medium, high
    soil_improvement: bool
    pest_resistance: List[str]
    disease_resistance: List[str]
    water_requirement: str     # low, medium, high
    growth_period: int         # days
    optimal_seasons: List[SeasonType]

@dataclass
class RotationPlan:
    field_id: str
    seasons: List[Dict[str, Any]]
    sustainability_score: float
    economic_score: float
    risk_score: float
    recommendations: List[str]

class CropRotationPlanner:
    def __init__(self, db_path: str = 'instance/agromap_dev.db'):
        self.db_path = db_path
        self.crop_compatibility = self._initialize_crop_compatibility()
        
    def _initialize_crop_compatibility(self) -> Dict[str, CropCompatibility]:
        """Initialize crop compatibility database"""
        return {
            'wheat': CropCompatibility(
                crop_type='wheat',
                nitrogen_requirement='medium',
                nitrogen_production='none',
                soil_improvement=False,
                pest_resistance=['aphid_resistance'],
                disease_resistance=['rust_tolerance'],
                water_requirement='medium',
                growth_period=120,
                optimal_seasons=[SeasonType.AUTUMN, SeasonType.SPRING]
            ),
            'cotton': CropCompatibility(
                crop_type='cotton',
                nitrogen_requirement='high',
                nitrogen_production='none',
                soil_improvement=False,
                pest_resistance=[],
                disease_resistance=['wilt_tolerance'],
                water_requirement='high',
                growth_period=180,
                optimal_seasons=[SeasonType.SPRING, SeasonType.SUMMER]
            ),
            'potato': CropCompatibility(
                crop_type='potato',
                nitrogen_requirement='medium',
                nitrogen_production='none',
                soil_improvement=False,
                pest_resistance=['nematode_resistance'],
                disease_resistance=['blight_tolerance'],
                water_requirement='medium',
                growth_period=90,
                optimal_seasons=[SeasonType.SPRING, SeasonType.AUTUMN]
            ),
            'alfalfa': CropCompatibility(
                crop_type='alfalfa',
                nitrogen_requirement='low',
                nitrogen_production='high',
                soil_improvement=True,
                pest_resistance=['general_pest_deterrent'],
                disease_resistance=[],
                water_requirement='medium',
                growth_period=365,  # Perennial
                optimal_seasons=[SeasonType.SPRING, SeasonType.SUMMER, SeasonType.AUTUMN]
            ),
            'corn': CropCompatibility(
                crop_type='corn',
                nitrogen_requirement='high',
                nitrogen_production='none',
                soil_improvement=False,
                pest_resistance=[],
                disease_resistance=['smut_tolerance'],
                water_requirement='high',
                growth_period=110,
                optimal_seasons=[SeasonType.SPRING, SeasonType.SUMMER]
            ),
            'beans': CropCompatibility(
                crop_type='beans',
                nitrogen_requirement='low',
                nitrogen_production='medium',
                soil_improvement=True,
                pest_resistance=['general_pest_deterrent'],
                disease_resistance=[],
                water_requirement='medium',
                growth_period=75,
                optimal_seasons=[SeasonType.SPRING, SeasonType.SUMMER]
            ),
            'barley': CropCompatibility(
                crop_type='barley',
                nitrogen_requirement='low',
                nitrogen_production='none',
                soil_improvement=False,
                pest_resistance=['aphid_resistance'],
                disease_resistance=['rust_tolerance'],
                water_requirement='low',
                growth_period=100,
                optimal_seasons=[SeasonType.AUTUMN, SeasonType.SPRING]
            ),
            'sunflower': CropCompatibility(
                crop_type='sunflower',
                nitrogen_requirement='medium',
                nitrogen_production='none',
                soil_improvement=False,
                pest_resistance=[],
                disease_resistance=['downy_mildew_tolerance'],
                water_requirement='medium',
                growth_period=110,
                optimal_seasons=[SeasonType.SPRING, SeasonType.SUMMER]
            )
        }
    
    def get_db_connection(self):
        """Get database connection"""
        try:
            conn = sqlite3.connect(self.db_path)
            conn.row_factory = sqlite3.Row
            return conn
        except Exception as e:
            logger.error(f"Database connection error: {e}")
            return None
    
    def generate_rotation_plan(self, 
                             field_location: Tuple[float, float],
                             field_size: float,
                             years: int = 3,
                             preferred_crops: List[str] = None,
                             avoid_crops: List[str] = None) -> RotationPlan:
        """Generate optimized crop rotation plan"""
        try:
            # Get historical data for the field location
            historical_data = self._get_field_history(field_location)
            
            # Analyze soil conditions and climate
            field_conditions = self._analyze_field_conditions(field_location, historical_data)
            
            # Generate season-by-season plan
            seasons = self._generate_seasonal_plan(
                field_conditions, years, preferred_crops, avoid_crops, historical_data
            )
            
            # Calculate scores
            sustainability_score = self._calculate_sustainability_score(seasons)
            economic_score = self._calculate_economic_score(seasons, field_size)
            risk_score = self._calculate_risk_score(seasons, field_conditions)
            
            # Generate recommendations
            recommendations = self._generate_rotation_recommendations(
                seasons, field_conditions, sustainability_score, economic_score, risk_score
            )
            
            return RotationPlan(
                field_id=f"{field_location[0]:.3f}_{field_location[1]:.3f}",
                seasons=seasons,
                sustainability_score=sustainability_score,
                economic_score=economic_score,
                risk_score=risk_score,
                recommendations=recommendations
            )
            
        except Exception as e:
            logger.error(f"Error generating rotation plan: {e}")
            return self._get_default_rotation_plan(field_location, years)
    
    def _get_field_history(self, location: Tuple[float, float]) -> List[Dict[str, Any]]:
        """Get historical crop data for nearby fields"""
        try:
            conn = self.get_db_connection()
            if not conn:
                return []
            
            lat, lng = location
            # Search within 0.01 degree radius (approximately 1km)
            cursor = conn.cursor()
            cursor.execute("""
                SELECT crop_type, field_size, timestamp, planting_date
                FROM crop_reports 
                WHERE latitude BETWEEN ? AND ? 
                AND longitude BETWEEN ? AND ?
                ORDER BY timestamp DESC
                LIMIT 50
            """, (lat - 0.01, lat + 0.01, lng - 0.01, lng + 0.01))
            
            history = cursor.fetchall()
            conn.close()
            
            return [dict(row) for row in history]
            
        except Exception as e:
            logger.error(f"Error getting field history: {e}")
            return []
    
    def _analyze_field_conditions(self, 
                                location: Tuple[float, float], 
                                history: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Analyze field conditions based on location and history"""
        # Mock field analysis - in real implementation, this would use:
        # - Soil type data
        # - Climate data
        # - Elevation data
        # - Historical weather patterns
        
        lat, lng = location
        
        # Determine climate zone based on latitude (simplified for Uzbekistan)
        if lat > 42:
            climate_zone = 'temperate'
            water_availability = 'limited'
        elif lat > 40:
            climate_zone = 'continental'
            water_availability = 'moderate'
        else:
            climate_zone = 'arid'
            water_availability = 'limited'
        
        # Analyze soil conditions from crop history
        if history:
            recent_crops = [h['crop_type'] for h in history[:10]]
            nitrogen_depleting_crops = ['wheat', 'cotton', 'corn', 'potato']
            nitrogen_fixing_crops = ['alfalfa', 'beans']
            
            depleting_count = sum(1 for crop in recent_crops if crop in nitrogen_depleting_crops)
            fixing_count = sum(1 for crop in recent_crops if crop in nitrogen_fixing_crops)
            
            if depleting_count > fixing_count * 2:
                soil_nitrogen = 'low'
            elif fixing_count > depleting_count:
                soil_nitrogen = 'high'
            else:
                soil_nitrogen = 'medium'
        else:
            soil_nitrogen = 'medium'
        
        return {
            'climate_zone': climate_zone,
            'water_availability': water_availability,
            'soil_nitrogen': soil_nitrogen,
            'soil_health': 'good',  # Simplified
            'pest_pressure': 'medium',
            'disease_pressure': 'medium'
        }
    
    def _generate_seasonal_plan(self, 
                              conditions: Dict[str, Any],
                              years: int,
                              preferred_crops: List[str] = None,
                              avoid_crops: List[str] = None,
                              history: List[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        """Generate season-by-season crop plan"""
        seasons = []
        available_crops = list(self.crop_compatibility.keys())
        
        # Filter crops based on preferences
        if preferred_crops:
            available_crops = [crop for crop in available_crops if crop in preferred_crops]
        if avoid_crops:
            available_crops = [crop for crop in available_crops if crop not in avoid_crops]
        
        # Get recent crops to avoid repetition
        recent_crops = []
        if history:
            recent_crops = [h['crop_type'] for h in history[:4]]  # Last 4 plantings
        
        current_season = self._get_current_season()
        nitrogen_level = conditions['soil_nitrogen']
        
        for year in range(years):
            for season_offset in range(2):  # Two main growing seasons per year
                season = self._get_season_by_offset(current_season, year * 2 + season_offset)
                
                # Select optimal crop for this season
                best_crop = self._select_optimal_crop(
                    available_crops, season, nitrogen_level, conditions, recent_crops
                )
                
                if best_crop:
                    crop_info = self.crop_compatibility[best_crop]
                    
                    # Update nitrogen level based on selected crop
                    if crop_info.nitrogen_production == 'high':
                        nitrogen_level = 'high'
                    elif crop_info.nitrogen_production == 'medium':
                        nitrogen_level = 'medium'
                    elif crop_info.nitrogen_requirement == 'high' and nitrogen_level == 'high':
                        nitrogen_level = 'medium'
                    elif crop_info.nitrogen_requirement == 'high' and nitrogen_level == 'medium':
                        nitrogen_level = 'low'
                    
                    # Add to recent crops for rotation consideration
                    recent_crops.append(best_crop)
                    if len(recent_crops) > 6:  # Keep last 6 seasons
                        recent_crops.pop(0)
                    
                    season_plan = {
                        'year': year + 1,
                        'season': season.value,
                        'crop_type': best_crop,
                        'expected_yield': self._estimate_yield(best_crop, conditions, nitrogen_level),
                        'nitrogen_level_after': nitrogen_level,
                        'sustainability_impact': self._assess_sustainability_impact(crop_info, conditions),
                        'economic_potential': self._assess_economic_potential(best_crop, season),
                        'risk_factors': self._identify_risk_factors(best_crop, conditions, recent_crops)
                    }
                    
                    seasons.append(season_plan)
        
        return seasons
    
    def _get_current_season(self) -> SeasonType:
        """Get current season based on date"""
        month = datetime.now().month
        if month in [12, 1, 2]:
            return SeasonType.WINTER
        elif month in [3, 4, 5]:
            return SeasonType.SPRING
        elif month in [6, 7, 8]:
            return SeasonType.SUMMER
        else:
            return SeasonType.AUTUMN
    
    def _get_season_by_offset(self, base_season: SeasonType, offset: int) -> SeasonType:
        """Get season by offset from base season"""
        seasons = [SeasonType.SPRING, SeasonType.SUMMER, SeasonType.AUTUMN, SeasonType.WINTER]
        base_index = seasons.index(base_season)
        new_index = (base_index + offset) % len(seasons)
        return seasons[new_index]
    
    def _select_optimal_crop(self, 
                           available_crops: List[str],
                           season: SeasonType,
                           nitrogen_level: str,
                           conditions: Dict[str, Any],
                           recent_crops: List[str]) -> Optional[str]:
        """Select optimal crop for given conditions"""
        scores = {}
        
        for crop in available_crops:
            if crop in recent_crops[-2:]:  # Avoid planting same crop in last 2 seasons
                continue
                
            crop_info = self.crop_compatibility[crop]
            score = 0
            
            # Season compatibility
            if season in crop_info.optimal_seasons:
                score += 30
            
            # Nitrogen management
            if nitrogen_level == 'low' and crop_info.nitrogen_requirement == 'low':
                score += 25
            elif nitrogen_level == 'low' and crop_info.nitrogen_production in ['medium', 'high']:
                score += 35  # Nitrogen-fixing crops are valuable when soil is depleted
            elif nitrogen_level == 'high' and crop_info.nitrogen_requirement == 'high':
                score += 25
            elif nitrogen_level == 'medium':
                score += 20  # Medium crops work well with medium nitrogen
            
            # Water requirements vs availability
            water_compatibility = self._assess_water_compatibility(
                crop_info.water_requirement, conditions['water_availability']
            )
            score += water_compatibility * 20
            
            # Soil improvement bonus
            if crop_info.soil_improvement:
                score += 15
            
            # Rotation diversity bonus
            if crop not in recent_crops:
                score += 10
            
            scores[crop] = score
        
        if not scores:
            return None
        
        # Return crop with highest score
        return max(scores, key=scores.get)
    
    def _assess_water_compatibility(self, crop_requirement: str, water_availability: str) -> float:
        """Assess compatibility between crop water requirements and availability"""
        compatibility_matrix = {
            ('low', 'limited'): 1.0,
            ('low', 'moderate'): 1.0,
            ('medium', 'limited'): 0.6,
            ('medium', 'moderate'): 1.0,
            ('high', 'limited'): 0.3,
            ('high', 'moderate'): 0.8
        }
        
        return compatibility_matrix.get((crop_requirement, water_availability), 0.5)
    
    def _estimate_yield(self, crop_type: str, conditions: Dict[str, Any], nitrogen_level: str) -> Dict[str, Any]:
        """Estimate crop yield based on conditions"""
        # Base yields (tons per hectare) - simplified estimates
        base_yields = {
            'wheat': 4.5,
            'cotton': 2.8,
            'potato': 25.0,
            'alfalfa': 12.0,
            'corn': 8.5,
            'beans': 2.2,
            'barley': 3.8,
            'sunflower': 2.5
        }
        
        base_yield = base_yields.get(crop_type, 3.0)
        
        # Adjust for nitrogen level
        nitrogen_multipliers = {'low': 0.8, 'medium': 1.0, 'high': 1.2}
        nitrogen_multiplier = nitrogen_multipliers.get(nitrogen_level, 1.0)
        
        # Adjust for water availability
        water_multipliers = {'limited': 0.85, 'moderate': 1.0, 'good': 1.15}
        water_multiplier = water_multipliers.get(conditions['water_availability'], 1.0)
        
        estimated_yield = base_yield * nitrogen_multiplier * water_multiplier
        
        return {
            'estimated_tons_per_hectare': round(estimated_yield, 2),
            'confidence': 'medium',  # Simplified confidence assessment
            'factors_considered': ['nitrogen_level', 'water_availability', 'climate_zone']
        }
    
    def _assess_sustainability_impact(self, crop_info: CropCompatibility, conditions: Dict[str, Any]) -> Dict[str, str]:
        """Assess sustainability impact of crop choice"""
        return {
            'soil_health': 'positive' if crop_info.soil_improvement else 'neutral',
            'nitrogen_balance': 'positive' if crop_info.nitrogen_production != 'none' else 'negative',
            'biodiversity': 'positive' if crop_info.pest_resistance else 'neutral',
            'water_efficiency': 'good' if crop_info.water_requirement == 'low' else 'moderate'
        }
    
    def _assess_economic_potential(self, crop_type: str, season: SeasonType) -> Dict[str, Any]:
        """Assess economic potential of crop in given season"""
        # Mock price data - in real implementation, use market data
        base_prices = {  # USD per ton
            'wheat': 200,
            'cotton': 1500,
            'potato': 300,
            'alfalfa': 150,
            'corn': 180,
            'beans': 800,
            'barley': 180,
            'sunflower': 400
        }
        
        base_price = base_prices.get(crop_type, 250)
        
        # Seasonal price adjustments (simplified)
        seasonal_multipliers = {
            SeasonType.SPRING: 1.0,
            SeasonType.SUMMER: 0.95,
            SeasonType.AUTUMN: 1.05,
            SeasonType.WINTER: 1.1
        }
        
        adjusted_price = base_price * seasonal_multipliers.get(season, 1.0)
        
        return {
            'estimated_price_per_ton': round(adjusted_price, 2),
            'market_demand': 'high' if crop_type in ['wheat', 'cotton'] else 'medium',
            'price_stability': 'stable' if crop_type in ['wheat', 'potato'] else 'volatile'
        }
    
    def _identify_risk_factors(self, crop_type: str, conditions: Dict[str, Any], recent_crops: List[str]) -> List[str]:
        """Identify risk factors for crop choice"""
        risks = []
        
        crop_info = self.crop_compatibility[crop_type]
        
        # Water stress risk
        if crop_info.water_requirement == 'high' and conditions['water_availability'] == 'limited':
            risks.append('High water stress risk')
        
        # Pest/disease buildup risk
        if recent_crops.count(crop_type) > 1:
            risks.append('Pest/disease buildup from repetitive planting')
        
        # Nitrogen deficiency risk
        if crop_info.nitrogen_requirement == 'high' and conditions['soil_nitrogen'] == 'low':
            risks.append('Nitrogen deficiency risk')
        
        # Market saturation risk
        if recent_crops.count(crop_type) > 2:
            risks.append('Potential market saturation in region')
        
        return risks
    
    def _calculate_sustainability_score(self, seasons: List[Dict[str, Any]]) -> float:
        """Calculate overall sustainability score for rotation plan"""
        if not seasons:
            return 0.0
        
        total_score = 0
        for season in seasons:
            # Crop diversity bonus
            if len(set(s['crop_type'] for s in seasons)) >= 3:
                total_score += 20
            
            # Nitrogen fixing bonus
            crop_info = self.crop_compatibility[season['crop_type']]
            if crop_info.nitrogen_production in ['medium', 'high']:
                total_score += 15
            
            # Soil improvement bonus
            if crop_info.soil_improvement:
                total_score += 10
            
            # Water efficiency bonus
            if crop_info.water_requirement == 'low':
                total_score += 5
        
        return min(total_score / len(seasons), 100.0)
    
    def _calculate_economic_score(self, seasons: List[Dict[str, Any]], field_size: float) -> float:
        """Calculate economic potential score"""
        if not seasons:
            return 0.0
        
        total_economic_value = 0
        for season in seasons:
            yield_data = season['expected_yield']
            economic_data = season['economic_potential']
            
            estimated_revenue = (yield_data['estimated_tons_per_hectare'] * 
                               economic_data['estimated_price_per_ton'] * 
                               field_size)
            total_economic_value += estimated_revenue
        
        # Normalize to 0-100 scale (simplified)
        avg_revenue_per_season = total_economic_value / len(seasons)
        economic_score = min(avg_revenue_per_season / 1000, 100.0)  # Normalize
        
        return round(economic_score, 1)
    
    def _calculate_risk_score(self, seasons: List[Dict[str, Any]], conditions: Dict[str, Any]) -> float:
        """Calculate risk score (lower is better)"""
        if not seasons:
            return 100.0
        
        total_risk = 0
        for season in seasons:
            risk_factors = season['risk_factors']
            total_risk += len(risk_factors) * 10  # 10 points per risk factor
        
        # Diversity risk - penalize monoculture
        unique_crops = len(set(s['crop_type'] for s in seasons))
        if unique_crops < 2:
            total_risk += 30
        elif unique_crops < 3:
            total_risk += 15
        
        avg_risk = total_risk / len(seasons)
        return min(avg_risk, 100.0)
    
    def _generate_rotation_recommendations(self, 
                                         seasons: List[Dict[str, Any]],
                                         conditions: Dict[str, Any],
                                         sustainability_score: float,
                                         economic_score: float,
                                         risk_score: float) -> List[str]:
        """Generate actionable recommendations"""
        recommendations = []
        
        # Sustainability recommendations
        if sustainability_score < 60:
            recommendations.append("Consider adding nitrogen-fixing crops like alfalfa or beans to improve soil health")
            recommendations.append("Increase crop diversity to enhance sustainability")
        
        # Economic recommendations
        if economic_score < 40:
            recommendations.append("Consider higher-value crops like cotton or sunflower for better economics")
            recommendations.append("Optimize planting timing to take advantage of seasonal price variations")
        
        # Risk management recommendations
        if risk_score > 50:
            recommendations.append("Reduce repetitive planting of the same crop to minimize pest/disease risks")
            recommendations.append("Consider drought-resistant varieties if water availability is limited")
        
        # General recommendations
        unique_crops = len(set(s['crop_type'] for s in seasons))
        if unique_crops < 3:
            recommendations.append("Implement 3+ crop rotation for optimal soil health and pest management")
        
        if conditions['soil_nitrogen'] == 'low':
            recommendations.append("Prioritize nitrogen-fixing crops in the next season")
        
        return recommendations
    
    def _get_default_rotation_plan(self, location: Tuple[float, float], years: int) -> RotationPlan:
        """Provide default rotation plan when analysis fails"""
        default_seasons = []
        crops = ['wheat', 'beans', 'potato', 'alfalfa']
        
        for year in range(years):
            for season_idx in range(2):
                crop = crops[(year * 2 + season_idx) % len(crops)]
                season_plan = {
                    'year': year + 1,
                    'season': 'spring' if season_idx == 0 else 'autumn',
                    'crop_type': crop,
                    'expected_yield': {'estimated_tons_per_hectare': 3.0, 'confidence': 'low'},
                    'nitrogen_level_after': 'medium',
                    'sustainability_impact': {'soil_health': 'neutral'},
                    'economic_potential': {'estimated_price_per_ton': 200, 'market_demand': 'medium'},
                    'risk_factors': []
                }
                default_seasons.append(season_plan)
        
        return RotationPlan(
            field_id=f"{location[0]:.3f}_{location[1]:.3f}",
            seasons=default_seasons,
            sustainability_score=65.0,
            economic_score=55.0,
            risk_score=35.0,
            recommendations=["This is a basic rotation plan. Consider consulting with local agricultural experts for optimization."]
        )
    
    def export_rotation_plan(self, plan: RotationPlan, format_type: str = 'json') -> str:
        """Export rotation plan in specified format"""
        try:
            if format_type.lower() == 'json':
                return json.dumps({
                    'field_id': plan.field_id,
                    'seasons': plan.seasons,
                    'scores': {
                        'sustainability': plan.sustainability_score,
                        'economic': plan.economic_score,
                        'risk': plan.risk_score
                    },
                    'recommendations': plan.recommendations
                }, indent=2, default=str)
            elif format_type.lower() == 'csv':
                return self._convert_plan_to_csv(plan)
            else:
                raise ValueError(f"Unsupported format: {format_type}")
        except Exception as e:
            logger.error(f"Error exporting rotation plan: {e}")
            return f"Error: {str(e)}"
    
    def _convert_plan_to_csv(self, plan: RotationPlan) -> str:
        """Convert rotation plan to CSV format"""
        csv_lines = [
            f"Field ID,{plan.field_id}",
            f"Sustainability Score,{plan.sustainability_score}",
            f"Economic Score,{plan.economic_score}",
            f"Risk Score,{plan.risk_score}",
            "",
            "Year,Season,Crop,Expected Yield (t/ha),Price ($/t)",
        ]
        
        for season in plan.seasons:
            csv_lines.append(
                f"{season['year']},{season['season']},{season['crop_type']},"
                f"{season['expected_yield']['estimated_tons_per_hectare']},"
                f"{season['economic_potential']['estimated_price_per_ton']}"
            )
        
        csv_lines.extend(["", "Recommendations:"])
        for i, rec in enumerate(plan.recommendations, 1):
            csv_lines.append(f"{i},{rec}")
        
        return "\n".join(csv_lines)

from datetime import datetime, timedelta
from app.models import CropReport
from app import db
from sqlalchemy import func
import math
import random

class MarketAnalyzer:
    def __init__(self):
        # Enhanced historical price data with confidence intervals (UZS per kg)
        self.historical_prices = {
            'wheat': {
                'prices': [2300, 2400, 2500, 2600, 2450, 2520, 2580, 2650, 2600, 2720],
                'volatility': 0.12,  # 12% price volatility
                'trend': 0.05,       # 5% annual growth trend
                'confidence': 0.85   # 85% confidence in historical data
            },
            'cotton': {
                'prices': [8200, 8400, 8500, 8300, 8600, 8450, 8500, 8750, 8650, 8900],
                'volatility': 0.18,
                'trend': 0.08,
                'confidence': 0.78
            },
            'potato': {
                'prices': [3000, 3200, 3100, 3300, 3250, 3180, 3200, 3350, 3280, 3400],
                'volatility': 0.22,
                'trend': 0.03,
                'confidence': 0.70
            },
            'corn': {
                'prices': [2800, 2900, 2850, 2950, 2920, 2980, 3000, 3050, 3020, 3100],
                'volatility': 0.15,
                'trend': 0.06,
                'confidence': 0.80
            },
            'rice': {
                'prices': [4500, 4600, 4550, 4700, 4650, 4720, 4800, 4850, 4900, 4950],
                'volatility': 0.10,
                'trend': 0.07,
                'confidence': 0.88
            }
        }
        
        # Enhanced seasonal price multipliers with regional variations
        self.seasonal_factors = {
            'wheat': {1: 1.1, 2: 1.15, 3: 1.2, 4: 1.0, 5: 0.9, 6: 0.85, 
                     7: 0.8, 8: 0.85, 9: 0.9, 10: 0.95, 11: 1.0, 12: 1.05},
            'cotton': {1: 0.9, 2: 0.95, 3: 1.0, 4: 1.1, 5: 1.2, 6: 1.15, 
                      7: 1.0, 8: 0.9, 9: 0.85, 10: 0.8, 11: 0.85, 12: 0.9},
            'potato': {1: 1.3, 2: 1.4, 3: 1.2, 4: 1.0, 5: 0.8, 6: 0.7, 
                      7: 0.8, 8: 0.9, 9: 1.0, 10: 1.1, 11: 1.2, 12: 1.25},
            'corn': {1: 1.2, 2: 1.25, 3: 1.1, 4: 0.95, 5: 0.85, 6: 0.8,
                    7: 0.85, 8: 0.9, 9: 1.0, 10: 1.05, 11: 1.1, 12: 1.15},
            'rice': {1: 1.05, 2: 1.1, 3: 1.15, 4: 1.0, 5: 0.95, 6: 0.9,
                    7: 0.85, 8: 0.9, 9: 0.95, 10: 1.0, 11: 1.02, 12: 1.03}
        }
        
        # Enhanced demand elasticity with market sophistication factors
        self.demand_elasticity = {
            'wheat': {'price_elasticity': -0.3, 'income_elasticity': 0.4, 'export_factor': 0.6},
            'cotton': {'price_elasticity': -0.8, 'income_elasticity': 1.2, 'export_factor': 0.9},
            'potato': {'price_elasticity': -0.5, 'income_elasticity': 0.6, 'export_factor': 0.3},
            'corn': {'price_elasticity': -0.4, 'income_elasticity': 0.7, 'export_factor': 0.5},
            'rice': {'price_elasticity': -0.3, 'income_elasticity': 0.5, 'export_factor': 0.7}
        }
        
        # Market intelligence factors
        self.market_intelligence = {
            'global_market_influence': {
                'wheat': 0.4,    # 40% influenced by global markets
                'cotton': 0.8,   # 80% influenced by global markets
                'potato': 0.2,   # 20% influenced by global markets
                'corn': 0.5,
                'rice': 0.6
            },
            'government_intervention': {
                'wheat': 0.3,    # 30% government price support
                'cotton': 0.6,   # 60% government involvement
                'potato': 0.1,   # 10% government intervention
                'corn': 0.2,
                'rice': 0.4
            },
            'storage_capacity': {
                'wheat': 0.7,    # 70% storage capacity utilization
                'cotton': 0.5,
                'potato': 0.3,   # Limited storage for perishables
                'corn': 0.6,
                'rice': 0.8
            }
        }

    def get_advanced_market_intelligence(self, crop_type, location_data=None):
        """Get comprehensive market intelligence with ML-inspired analytics"""
        current_month = datetime.now().month
        
        # Base price calculation
        if crop_type in self.historical_prices:
            price_data = self.historical_prices[crop_type]
            base_price = price_data['prices'][-1]  # Latest price
            
            # Apply seasonal factors
            seasonal_multiplier = self.seasonal_factors.get(crop_type, {}).get(current_month, 1.0)
            seasonal_price = base_price * seasonal_multiplier
            
            # Calculate price volatility and confidence bands
            volatility = price_data['volatility']
            confidence = price_data['confidence']
            
            # Price range calculation (confidence intervals)
            price_range = {
                'low': seasonal_price * (1 - volatility),
                'high': seasonal_price * (1 + volatility),
                'expected': seasonal_price
            }
            
            # Supply-demand analysis
            supply_demand = self._analyze_supply_demand(crop_type, location_data)
            
            # Market trend analysis
            trend_analysis = self._calculate_market_trends(crop_type)
            
            # Risk assessment
            risk_assessment = self._assess_market_risks(crop_type)
            
            # Price prediction with confidence intervals
            price_forecast = self._predict_future_prices(crop_type, 3)  # 3-month forecast
            
            return {
                'crop_type': crop_type,
                'current_price_analysis': {
                    'base_price': round(base_price, 2),
                    'seasonal_adjusted': round(seasonal_price, 2),
                    'price_range': {
                        'low': round(price_range['low'], 2),
                        'expected': round(price_range['expected'], 2),
                        'high': round(price_range['high'], 2)
                    },
                    'volatility_index': volatility,
                    'confidence_score': confidence
                },
                'supply_demand': supply_demand,
                'trend_analysis': trend_analysis,
                'risk_assessment': risk_assessment,
                'price_forecast': price_forecast,
                'market_intelligence': self._get_market_intelligence_summary(crop_type),
                'trading_recommendations': self._generate_trading_recommendations(crop_type, supply_demand, trend_analysis),
                'optimal_timing': self._calculate_optimal_timing(crop_type)
            }
        
        return None

    def _analyze_supply_demand(self, crop_type, location_data=None):
        """Analyze supply and demand dynamics with regional factors"""
        try:
            # Get current planting reports
            query = CropReport.query.filter_by(crop_type=crop_type, public=True)
            
            # Regional filtering if location provided
            if location_data:
                # Filter within 100km radius for local market analysis
                radius = 100  # km
                lat = location_data.get('latitude', 41.3775)
                lng = location_data.get('longitude', 64.5853)
                
                # Approximate geographic filtering (simplified)
                lat_range = radius / 111.0  # Rough conversion to degrees
                lng_range = radius / (111.0 * math.cos(math.radians(lat)))
                
                query = query.filter(
                    CropReport.latitude.between(lat - lat_range, lat + lat_range),
                    CropReport.longitude.between(lng - lng_range, lng + lng_range)
                )
            
            recent_reports = query.filter(
                CropReport.created_at >= datetime.now() - timedelta(days=30)
            ).all()
            
            # Calculate supply metrics
            total_planted_area = sum(report.area for report in recent_reports if report.area)
            avg_yield_reports = len([r for r in recent_reports if r.yield_actual])
            
            # Demand calculation based on regional factors
            regional_demand = self._calculate_regional_demand(crop_type, location_data)
            
            # Supply-demand balance
            if total_planted_area > 0:
                supply_index = min(total_planted_area / 1000, 1.0)  # Normalize to 0-1
                demand_supply_ratio = regional_demand / max(supply_index, 0.1)
            else:
                supply_index = 0.3  # Default moderate supply
                demand_supply_ratio = 2.0  # High demand, low supply
            
            # Market pressure indicators
            market_pressure = self._calculate_market_pressure(crop_type, demand_supply_ratio)
            
            return {
                'supply_index': round(supply_index, 2),
                'demand_index': round(regional_demand, 2),
                'demand_supply_ratio': round(demand_supply_ratio, 2),
                'market_balance': self._interpret_market_balance(demand_supply_ratio),
                'supply_pressure': market_pressure['supply_pressure'],
                'demand_pressure': market_pressure['demand_pressure'],
                'market_sentiment': market_pressure['sentiment'],
                'planted_area_trend': self._calculate_planting_trend(crop_type)
            }
            
        except Exception as e:
            # Default supply-demand analysis if database query fails
            return {
                'supply_index': 0.6,
                'demand_index': 0.7,
                'demand_supply_ratio': 1.17,
                'market_balance': 'slightly_tight',
                'supply_pressure': 'moderate',
                'demand_pressure': 'moderate_high',
                'market_sentiment': 'cautiously_optimistic',
                'planted_area_trend': 'stable'
            }

    def _calculate_regional_demand(self, crop_type, location_data):
        """Calculate regional demand based on population and economic factors"""
        # Base demand factors (simplified model)
        base_demand = {
            'wheat': 0.8,    # High staple demand
            'cotton': 0.6,   # Industrial/export demand
            'potato': 0.7,   # Food demand
            'corn': 0.5,     # Feed/food demand
            'rice': 0.6      # Regional food preference
        }
        
        # Regional demand multipliers (mock data)
        if location_data:
            # Simulate regional economic factors
            lat = location_data.get('latitude', 41.3775)
            lng = location_data.get('longitude', 64.5853)
            
            # Urban areas have higher demand (simplified calculation)
            urban_factor = 1.0
            if abs(lat - 41.2995) < 0.5 and abs(lng - 69.2401) < 0.5:  # Near Tashkent
                urban_factor = 1.3
            elif abs(lat - 40.3833) < 0.5 and abs(lng - 71.7833) < 0.5:  # Near Fergana
                urban_factor = 1.2
            
            return base_demand.get(crop_type, 0.5) * urban_factor
        
        return base_demand.get(crop_type, 0.5)

    def _calculate_market_pressure(self, crop_type, demand_supply_ratio):
        """Calculate market pressure indicators"""
        if demand_supply_ratio > 1.5:
            return {
                'supply_pressure': 'high',
                'demand_pressure': 'very_high',
                'sentiment': 'bullish'
            }
        elif demand_supply_ratio > 1.2:
            return {
                'supply_pressure': 'moderate_high',
                'demand_pressure': 'high',
                'sentiment': 'optimistic'
            }
        elif demand_supply_ratio > 0.8:
            return {
                'supply_pressure': 'moderate',
                'demand_pressure': 'moderate',
                'sentiment': 'neutral'
            }
        elif demand_supply_ratio > 0.6:
            return {
                'supply_pressure': 'low',
                'demand_pressure': 'low',
                'sentiment': 'cautious'
            }
        else:
            return {
                'supply_pressure': 'very_low',
                'demand_pressure': 'very_low',
                'sentiment': 'bearish'
            }

    def _interpret_market_balance(self, ratio):
        """Interpret demand-supply ratio"""
        if ratio > 1.3:
            return 'tight'
        elif ratio > 1.1:
            return 'slightly_tight'
        elif ratio > 0.9:
            return 'balanced'
        elif ratio > 0.7:
            return 'slightly_loose'
        else:
            return 'oversupplied'

    def _calculate_market_trends(self, crop_type):
        """Calculate market trend analysis using technical indicators"""
        if crop_type not in self.historical_prices:
            return {'trend': 'neutral', 'strength': 'weak', 'direction': 'sideways'}
        
        prices = self.historical_prices[crop_type]['prices']
        if len(prices) < 5:
            return {'trend': 'neutral', 'strength': 'weak', 'direction': 'sideways'}
        
        # Simple moving averages
        short_ma = sum(prices[-3:]) / 3
        long_ma = sum(prices[-7:]) / 7
        
        # Trend direction
        if short_ma > long_ma * 1.05:
            direction = 'upward'
            trend = 'bullish'
        elif short_ma < long_ma * 0.95:
            direction = 'downward'
            trend = 'bearish'
        else:
            direction = 'sideways'
            trend = 'neutral'
        
        # Trend strength based on price momentum
        recent_change = (prices[-1] - prices[-3]) / prices[-3] if prices[-3] != 0 else 0
        if abs(recent_change) > 0.1:
            strength = 'strong'
        elif abs(recent_change) > 0.05:
            strength = 'moderate'
        else:
            strength = 'weak'
        
        return {
            'trend': trend,
            'direction': direction,
            'strength': strength,
            'momentum': round(recent_change * 100, 2),  # Percentage change
            'short_ma': round(short_ma, 2),
            'long_ma': round(long_ma, 2)
        }

    def _assess_market_risks(self, crop_type):
        """Assess various market risks"""
        volatility = self.historical_prices.get(crop_type, {}).get('volatility', 0.15)
        global_influence = self.market_intelligence['global_market_influence'].get(crop_type, 0.5)
        storage_capacity = self.market_intelligence['storage_capacity'].get(crop_type, 0.5)
        
        # Risk scoring
        price_risk = 'high' if volatility > 0.2 else 'moderate' if volatility > 0.1 else 'low'
        global_risk = 'high' if global_influence > 0.7 else 'moderate' if global_influence > 0.4 else 'low'
        storage_risk = 'high' if storage_capacity < 0.4 else 'moderate' if storage_capacity < 0.7 else 'low'
        
        # Overall risk assessment
        risk_scores = {'low': 1, 'moderate': 2, 'high': 3}
        avg_risk = (risk_scores[price_risk] + risk_scores[global_risk] + risk_scores[storage_risk]) / 3
        
        if avg_risk >= 2.5:
            overall_risk = 'high'
        elif avg_risk >= 1.5:
            overall_risk = 'moderate'
        else:
            overall_risk = 'low'
        
        return {
            'overall_risk': overall_risk,
            'price_volatility_risk': price_risk,
            'global_market_risk': global_risk,
            'storage_risk': storage_risk,
            'risk_score': round(avg_risk, 2),
            'risk_factors': self._identify_key_risk_factors(crop_type)
        }

    def _identify_key_risk_factors(self, crop_type):
        """Identify key risk factors for the crop"""
        risk_factors = []
        
        volatility = self.historical_prices.get(crop_type, {}).get('volatility', 0.15)
        if volatility > 0.2:
            risk_factors.append('High price volatility')
        
        global_influence = self.market_intelligence['global_market_influence'].get(crop_type, 0.5)
        if global_influence > 0.7:
            risk_factors.append('High global market exposure')
        
        storage_capacity = self.market_intelligence['storage_capacity'].get(crop_type, 0.5)
        if storage_capacity < 0.4:
            risk_factors.append('Limited storage capacity')
        
        # Seasonal risks
        current_month = datetime.now().month
        seasonal_factor = self.seasonal_factors.get(crop_type, {}).get(current_month, 1.0)
        if seasonal_factor > 1.2:
            risk_factors.append('Seasonal price premium period')
        elif seasonal_factor < 0.8:
            risk_factors.append('Seasonal price depression period')
        
        return risk_factors[:3]  # Return top 3 risk factors

    def _predict_future_prices(self, crop_type, months_ahead):
        """Predict future prices using trend analysis and seasonal factors"""
        if crop_type not in self.historical_prices:
            return []
        
        current_price = self.historical_prices[crop_type]['prices'][-1]
        trend = self.historical_prices[crop_type]['trend']
        volatility = self.historical_prices[crop_type]['volatility']
        
        forecasts = []
        current_month = datetime.now().month
        
        for i in range(1, months_ahead + 1):
            future_month = (current_month + i - 1) % 12 + 1
            
            # Apply trend
            trend_factor = (1 + trend / 12) ** i  # Monthly compounding
            
            # Apply seasonal factors
            seasonal_factor = self.seasonal_factors.get(crop_type, {}).get(future_month, 1.0)
            
            # Add some randomness for volatility
            volatility_factor = 1 + random.uniform(-volatility/2, volatility/2)
            
            predicted_price = current_price * trend_factor * seasonal_factor * volatility_factor
            
            # Confidence decreases over time
            confidence = max(0.5, 0.9 - (i * 0.1))
            
            forecasts.append({
                'month': future_month,
                'predicted_price': round(predicted_price, 2),
                'confidence': round(confidence, 2),
                'price_range': {
                    'low': round(predicted_price * (1 - volatility), 2),
                    'high': round(predicted_price * (1 + volatility), 2)
                }
            })
        
        return forecasts

    def _get_market_intelligence_summary(self, crop_type):
        """Get market intelligence summary"""
        return {
            'global_market_influence': self.market_intelligence['global_market_influence'].get(crop_type, 0.5),
            'government_intervention_level': self.market_intelligence['government_intervention'].get(crop_type, 0.3),
            'storage_capacity_utilization': self.market_intelligence['storage_capacity'].get(crop_type, 0.5),
            'export_potential': self._calculate_export_potential(crop_type),
            'market_maturity': self._assess_market_maturity(crop_type)
        }

    def _calculate_export_potential(self, crop_type):
        """Calculate export potential based on various factors"""
        export_factors = {
            'wheat': 0.3,   # Limited export due to domestic consumption
            'cotton': 0.9,  # High export potential
            'potato': 0.4,  # Moderate export potential
            'corn': 0.5,    # Moderate export potential
            'rice': 0.6     # Good export potential
        }
        return export_factors.get(crop_type, 0.5)

    def _assess_market_maturity(self, crop_type):
        """Assess market maturity level"""
        maturity_levels = {
            'wheat': 'mature',
            'cotton': 'mature',
            'potato': 'developing',
            'corn': 'developing',
            'rice': 'established'
        }
        return maturity_levels.get(crop_type, 'developing')

    def _generate_trading_recommendations(self, crop_type, supply_demand, trend_analysis):
        """Generate trading recommendations based on analysis"""
        recommendations = []
        
        # Price-based recommendations
        if supply_demand['demand_supply_ratio'] > 1.3:
            recommendations.append({
                'type': 'sell',
                'confidence': 'high',
                'reason': 'High demand-supply ratio indicates favorable selling conditions'
            })
        elif supply_demand['demand_supply_ratio'] < 0.8:
            recommendations.append({
                'type': 'hold',
                'confidence': 'moderate',
                'reason': 'Oversupply conditions suggest waiting for better prices'
            })
        
        # Trend-based recommendations
        if trend_analysis['trend'] == 'bullish' and trend_analysis['strength'] == 'strong':
            recommendations.append({
                'type': 'hold_for_appreciation',
                'confidence': 'high',
                'reason': 'Strong upward trend suggests prices may continue rising'
            })
        elif trend_analysis['trend'] == 'bearish' and trend_analysis['strength'] == 'strong':
            recommendations.append({
                'type': 'sell_quickly',
                'confidence': 'moderate',
                'reason': 'Strong downward trend suggests immediate action needed'
            })
        
        # Seasonal recommendations
        current_month = datetime.now().month
        seasonal_factor = self.seasonal_factors.get(crop_type, {}).get(current_month, 1.0)
        if seasonal_factor > 1.15:
            recommendations.append({
                'type': 'sell',
                'confidence': 'moderate',
                'reason': 'Seasonal price premium period - good time to sell'
            })
        
        return recommendations[:3]  # Return top 3 recommendations

    def _calculate_optimal_timing(self, crop_type):
        """Calculate optimal timing for planting and selling"""
        # Find best planting months (lowest seasonal factors for cost optimization)
        planting_scores = {}
        for month, factor in self.seasonal_factors.get(crop_type, {}).items():
            # Lower seasonal factor means lower input costs
            planting_scores[month] = 1 / factor
        
        # Find best selling months (highest seasonal factors)
        selling_scores = self.seasonal_factors.get(crop_type, {})
        
        # Get top 3 months for each
        best_planting = sorted(planting_scores.items(), key=lambda x: x[1], reverse=True)[:3]
        best_selling = sorted(selling_scores.items(), key=lambda x: x[1], reverse=True)[:3]
        
        return {
            'optimal_planting_months': [{'month': m, 'score': round(s, 2)} for m, s in best_planting],
            'optimal_selling_months': [{'month': m, 'score': round(s, 2)} for m, s in best_selling],
            'current_month_rating': self._rate_current_timing(crop_type)
        }

    def _rate_current_timing(self, crop_type):
        """Rate current month for planting/selling decisions"""
        current_month = datetime.now().month
        seasonal_factor = self.seasonal_factors.get(crop_type, {}).get(current_month, 1.0)
        
        if seasonal_factor > 1.2:
            return {'rating': 'excellent_for_selling', 'score': 5}
        elif seasonal_factor > 1.1:
            return {'rating': 'good_for_selling', 'score': 4}
        elif seasonal_factor > 0.9:
            return {'rating': 'neutral', 'score': 3}
        elif seasonal_factor > 0.8:
            return {'rating': 'good_for_buying', 'score': 2}
        else:
            return {'rating': 'excellent_for_buying', 'score': 1}

    def _calculate_planting_trend(self, crop_type):
        """Calculate planting area trend"""
        try:
            # Get planting data from recent months
            recent_date = datetime.now() - timedelta(days=90)
            older_date = datetime.now() - timedelta(days=180)
            
            recent_count = CropReport.query.filter_by(crop_type=crop_type, public=True).filter(
                CropReport.created_at >= recent_date
            ).count()
            
            older_count = CropReport.query.filter_by(crop_type=crop_type, public=True).filter(
                CropReport.created_at.between(older_date, recent_date)
            ).count()
            
            if older_count > 0:
                change_ratio = recent_count / older_count
                if change_ratio > 1.2:
                    return 'increasing'
                elif change_ratio < 0.8:
                    return 'decreasing'
                else:
                    return 'stable'
            else:
                return 'stable'
                
        except Exception:
            return 'stable'

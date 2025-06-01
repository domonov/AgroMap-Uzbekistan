"""
Advanced Analytics Service for AgroMap Uzbekistan
Provides comprehensive data analysis, reporting, and insights
"""

import sqlite3
import json
import pandas as pd
from datetime import datetime, timedelta
from collections import defaultdict, Counter
import numpy as np
from typing import Dict, List, Any, Optional, Tuple
import logging

logger = logging.getLogger(__name__)

class AnalyticsService:
    def __init__(self, db_path: str = 'instance/agromap_dev.db'):
        self.db_path = db_path
        
    def get_db_connection(self):
        """Get database connection"""
        try:
            conn = sqlite3.connect(self.db_path)
            conn.row_factory = sqlite3.Row
            return conn
        except Exception as e:
            logger.error(f"Database connection error: {e}")
            return None
    
    def get_comprehensive_dashboard_data(self) -> Dict[str, Any]:
        """Get comprehensive analytics data for dashboard"""
        try:
            conn = self.get_db_connection()
            if not conn:
                return self._get_mock_dashboard_data()
            
            # Get basic statistics
            basic_stats = self._get_basic_statistics(conn)
            
            # Get crop diversity analysis
            diversity_analysis = self._get_crop_diversity_analysis(conn)
            
            # Get temporal trends
            temporal_trends = self._get_temporal_trends(conn)
            
            # Get geographic distribution
            geographic_data = self._get_geographic_distribution(conn)
            
            # Get yield efficiency analysis
            efficiency_analysis = self._get_yield_efficiency_analysis(conn)
            
            # Get market readiness indicators
            market_indicators = self._get_market_readiness_indicators(conn)
            
            # Get sustainability metrics
            sustainability_metrics = self._get_sustainability_metrics(conn)
            
            conn.close()
            
            return {
                'basic_stats': basic_stats,
                'diversity_analysis': diversity_analysis,
                'temporal_trends': temporal_trends,
                'geographic_data': geographic_data,
                'efficiency_analysis': efficiency_analysis,
                'market_indicators': market_indicators,
                'sustainability_metrics': sustainability_metrics,
                'generated_at': datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error generating dashboard data: {e}")
            return self._get_mock_dashboard_data()
    
    def _get_basic_statistics(self, conn) -> Dict[str, Any]:
        """Get basic agricultural statistics"""
        cursor = conn.cursor()
        
        # Total reports and area
        cursor.execute("SELECT COUNT(*) as total_reports, SUM(field_size) as total_area FROM crop_reports")
        basic_data = cursor.fetchone()
        
        # Crop type distribution
        cursor.execute("""
            SELECT crop_type, COUNT(*) as count, SUM(field_size) as total_area
            FROM crop_reports 
            GROUP BY crop_type 
            ORDER BY total_area DESC
        """)
        crop_distribution = cursor.fetchall()
        
        # Recent activity (last 30 days)
        thirty_days_ago = (datetime.now() - timedelta(days=30)).strftime('%Y-%m-%d')
        cursor.execute("""
            SELECT COUNT(*) as recent_reports, SUM(field_size) as recent_area
            FROM crop_reports 
            WHERE timestamp >= ?
        """, (thirty_days_ago,))
        recent_data = cursor.fetchone()
        
        return {
            'total_reports': basic_data['total_reports'] or 0,
            'total_area': round(basic_data['total_area'] or 0, 2),
            'crop_distribution': [dict(row) for row in crop_distribution],
            'recent_reports': recent_data['recent_reports'] or 0,
            'recent_area': round(recent_data['recent_area'] or 0, 2),
            'avg_field_size': round((basic_data['total_area'] or 0) / max(basic_data['total_reports'] or 1, 1), 2)
        }
    
    def _get_crop_diversity_analysis(self, conn) -> Dict[str, Any]:
        """Analyze crop diversity and distribution patterns"""
        cursor = conn.cursor()
        
        # Crop diversity index (Shannon diversity)
        cursor.execute("SELECT crop_type, COUNT(*) as count FROM crop_reports GROUP BY crop_type")
        crop_counts = cursor.fetchall()
        
        total_reports = sum(row['count'] for row in crop_counts)
        if total_reports == 0:
            diversity_index = 0
        else:
            proportions = [row['count'] / total_reports for row in crop_counts]
            diversity_index = -sum(p * np.log(p) for p in proportions if p > 0)
        
        # Area concentration analysis
        cursor.execute("""
            SELECT crop_type, SUM(field_size) as total_area, AVG(field_size) as avg_size
            FROM crop_reports 
            GROUP BY crop_type
        """)
        area_analysis = cursor.fetchall()
        
        return {
            'diversity_index': round(diversity_index, 3),
            'crop_count': len(crop_counts),
            'area_distribution': [dict(row) for row in area_analysis],
            'concentration_metrics': self._calculate_concentration_metrics(area_analysis)
        }
    
    def _get_temporal_trends(self, conn) -> Dict[str, Any]:
        """Analyze temporal planting trends"""
        cursor = conn.cursor()
        
        # Monthly planting trends
        cursor.execute("""
            SELECT 
                strftime('%Y-%m', timestamp) as month,
                crop_type,
                COUNT(*) as count,
                SUM(field_size) as area
            FROM crop_reports 
            WHERE timestamp >= date('now', '-12 months')
            GROUP BY month, crop_type
            ORDER BY month DESC
        """)
        monthly_data = cursor.fetchall()
        
        # Seasonal patterns
        cursor.execute("""
            SELECT 
                CASE 
                    WHEN CAST(strftime('%m', timestamp) AS INTEGER) IN (12, 1, 2) THEN 'Winter'
                    WHEN CAST(strftime('%m', timestamp) AS INTEGER) IN (3, 4, 5) THEN 'Spring'
                    WHEN CAST(strftime('%m', timestamp) AS INTEGER) IN (6, 7, 8) THEN 'Summer'
                    ELSE 'Autumn'
                END as season,
                crop_type,
                COUNT(*) as count,
                SUM(field_size) as area
            FROM crop_reports 
            GROUP BY season, crop_type
        """)
        seasonal_data = cursor.fetchall()
        
        return {
            'monthly_trends': [dict(row) for row in monthly_data],
            'seasonal_patterns': [dict(row) for row in seasonal_data],
            'growth_rate': self._calculate_growth_rate(monthly_data)
        }
    
    def _get_geographic_distribution(self, conn) -> Dict[str, Any]:
        """Analyze geographic distribution patterns"""
        cursor = conn.cursor()
        
        # Regional clustering analysis
        cursor.execute("""
            SELECT 
                ROUND(latitude, 1) as lat_group,
                ROUND(longitude, 1) as lng_group,
                crop_type,
                COUNT(*) as count,
                SUM(field_size) as area
            FROM crop_reports 
            GROUP BY lat_group, lng_group, crop_type
        """)
        regional_data = cursor.fetchall()
        
        # Density analysis
        cursor.execute("""
            SELECT 
                latitude, longitude, field_size,
                COUNT(*) OVER (
                    PARTITION BY ROUND(latitude, 2), ROUND(longitude, 2)
                ) as local_density
            FROM crop_reports
        """)
        density_data = cursor.fetchall()
        
        return {
            'regional_clusters': [dict(row) for row in regional_data],
            'density_analysis': self._analyze_density_patterns(density_data),
            'geographic_spread': self._calculate_geographic_spread(regional_data)
        }
    
    def _get_yield_efficiency_analysis(self, conn) -> Dict[str, Any]:
        """Analyze yield efficiency and optimization opportunities"""
        cursor = conn.cursor()
        
        # Field size efficiency analysis
        cursor.execute("""
            SELECT 
                crop_type,
                CASE 
                    WHEN field_size < 1 THEN 'Small (< 1 ha)'
                    WHEN field_size < 5 THEN 'Medium (1-5 ha)'
                    WHEN field_size < 20 THEN 'Large (5-20 ha)'
                    ELSE 'Very Large (> 20 ha)'
                END as size_category,
                COUNT(*) as count,
                AVG(field_size) as avg_size,
                SUM(field_size) as total_area
            FROM crop_reports 
            GROUP BY crop_type, size_category
        """)
        efficiency_data = cursor.fetchall()
        
        return {
            'size_efficiency': [dict(row) for row in efficiency_data],
            'optimization_opportunities': self._identify_optimization_opportunities(efficiency_data),
            'efficiency_score': self._calculate_efficiency_score(efficiency_data)
        }
    
    def _get_market_readiness_indicators(self, conn) -> Dict[str, Any]:
        """Calculate market readiness and supply indicators"""
        cursor = conn.cursor()
        
        # Current supply estimation
        cursor.execute("""
            SELECT 
                crop_type,
                SUM(field_size) as total_area,
                COUNT(*) as farm_count,
                AVG(field_size) as avg_field_size
            FROM crop_reports 
            GROUP BY crop_type
        """)
        supply_data = cursor.fetchall()
        
        # Market saturation indicators
        market_indicators = []
        for crop in supply_data:
            saturation_score = self._calculate_market_saturation(crop)
            market_indicators.append({
                'crop_type': crop['crop_type'],
                'supply_area': crop['total_area'],
                'farm_count': crop['farm_count'],
                'saturation_score': saturation_score,
                'market_status': self._get_market_status(saturation_score)
            })
        
        return {
            'supply_indicators': market_indicators,
            'market_balance': self._calculate_market_balance(supply_data),
            'recommendations': self._generate_market_recommendations(market_indicators)
        }
    
    def _get_sustainability_metrics(self, conn) -> Dict[str, Any]:
        """Calculate sustainability and environmental metrics"""
        cursor = conn.cursor()
        
        # Crop rotation analysis
        cursor.execute("""
            SELECT 
                ROUND(latitude, 3) as lat,
                ROUND(longitude, 3) as lng,
                crop_type,
                timestamp,
                field_size
            FROM crop_reports 
            ORDER BY lat, lng, timestamp
        """)
        rotation_data = cursor.fetchall()
        
        sustainability_score = self._calculate_sustainability_score(rotation_data)
        
        return {
            'sustainability_score': sustainability_score,
            'rotation_analysis': self._analyze_crop_rotation(rotation_data),
            'environmental_impact': self._assess_environmental_impact(rotation_data),
            'recommendations': self._generate_sustainability_recommendations(sustainability_score)
        }
    
    def export_analytics_data(self, format_type: str = 'json') -> str:
        """Export analytics data in specified format"""
        try:
            data = self.get_comprehensive_dashboard_data()
            
            if format_type.lower() == 'json':
                return json.dumps(data, indent=2, default=str)
            elif format_type.lower() == 'csv':
                return self._convert_to_csv(data)
            else:
                raise ValueError(f"Unsupported format: {format_type}")
                
        except Exception as e:
            logger.error(f"Error exporting analytics data: {e}")
            return f"Error: {str(e)}"
    
    def _convert_to_csv(self, data: Dict[str, Any]) -> str:
        """Convert analytics data to CSV format"""
        csv_data = []
        
        # Basic statistics
        basic = data['basic_stats']
        csv_data.append("Basic Statistics")
        csv_data.append(f"Total Reports,{basic['total_reports']}")
        csv_data.append(f"Total Area (ha),{basic['total_area']}")
        csv_data.append(f"Average Field Size (ha),{basic['avg_field_size']}")
        csv_data.append("")
        
        # Crop distribution
        csv_data.append("Crop Distribution")
        csv_data.append("Crop Type,Count,Total Area")
        for crop in basic['crop_distribution']:
            csv_data.append(f"{crop['crop_type']},{crop['count']},{crop['total_area']}")
        
        return "\n".join(csv_data)
    
    # Helper methods for calculations
    def _calculate_concentration_metrics(self, area_data) -> Dict[str, float]:
        """Calculate concentration metrics for crop areas"""
        if not area_data:
            return {'gini_coefficient': 0, 'herfindahl_index': 0}
        
        areas = [row['total_area'] for row in area_data]
        total_area = sum(areas)
        
        if total_area == 0:
            return {'gini_coefficient': 0, 'herfindahl_index': 0}
        
        # Gini coefficient
        areas.sort()
        n = len(areas)
        index = np.arange(1, n + 1)
        gini = (2 * np.sum(index * areas)) / (n * np.sum(areas)) - (n + 1) / n
        
        # Herfindahl index
        market_shares = [area / total_area for area in areas]
        herfindahl = sum(share ** 2 for share in market_shares)
        
        return {
            'gini_coefficient': round(gini, 3),
            'herfindahl_index': round(herfindahl, 3)
        }
    
    def _calculate_growth_rate(self, monthly_data) -> float:
        """Calculate growth rate from monthly data"""
        if len(monthly_data) < 2:
            return 0.0
        
        # Group by month and sum areas
        monthly_totals = defaultdict(float)
        for row in monthly_data:
            monthly_totals[row['month']] += row['area']
        
        if len(monthly_totals) < 2:
            return 0.0
        
        months = sorted(monthly_totals.keys())
        latest = monthly_totals[months[-1]]
        previous = monthly_totals[months[-2]]
        
        if previous == 0:
            return 0.0
        
        return round(((latest - previous) / previous) * 100, 2)
    
    def _analyze_density_patterns(self, density_data) -> Dict[str, Any]:
        """Analyze farming density patterns"""
        if not density_data:
            return {'avg_density': 0, 'max_density': 0, 'density_distribution': []}
        
        densities = [row['local_density'] for row in density_data]
        
        return {
            'avg_density': round(np.mean(densities), 2),
            'max_density': max(densities),
            'density_distribution': {
                'low': sum(1 for d in densities if d <= 2),
                'medium': sum(1 for d in densities if 2 < d <= 5),
                'high': sum(1 for d in densities if d > 5)
            }
        }
    
    def _calculate_geographic_spread(self, regional_data) -> Dict[str, float]:
        """Calculate geographic spread metrics"""
        if not regional_data:
            return {'lat_range': 0, 'lng_range': 0, 'coverage_area': 0}
        
        lats = [row['lat_group'] for row in regional_data]
        lngs = [row['lng_group'] for row in regional_data]
        
        return {
            'lat_range': round(max(lats) - min(lats), 2),
            'lng_range': round(max(lngs) - min(lngs), 2),
            'coverage_area': round((max(lats) - min(lats)) * (max(lngs) - min(lngs)), 2)
        }
    
    def _identify_optimization_opportunities(self, efficiency_data) -> List[Dict[str, Any]]:
        """Identify optimization opportunities"""
        opportunities = []
        
        crop_sizes = defaultdict(list)
        for row in efficiency_data:
            crop_sizes[row['crop_type']].append({
                'category': row['size_category'],
                'count': row['count'],
                'avg_size': row['avg_size']
            })
        
        for crop, sizes in crop_sizes.items():
            small_farms = sum(s['count'] for s in sizes if 'Small' in s['category'])
            total_farms = sum(s['count'] for s in sizes)
            
            if small_farms / total_farms > 0.7:  # More than 70% small farms
                opportunities.append({
                    'crop_type': crop,
                    'opportunity': 'Farm consolidation',
                    'potential_improvement': 'Increase efficiency through larger field sizes',
                    'priority': 'High' if small_farms / total_farms > 0.8 else 'Medium'
                })
        
        return opportunities
    
    def _calculate_efficiency_score(self, efficiency_data) -> float:
        """Calculate overall efficiency score"""
        if not efficiency_data:
            return 0.0
        
        # Score based on field size distribution
        total_count = sum(row['count'] for row in efficiency_data)
        if total_count == 0:
            return 0.0
        
        score = 0
        for row in efficiency_data:
            weight = row['count'] / total_count
            if 'Small' in row['size_category']:
                score += weight * 0.3
            elif 'Medium' in row['size_category']:
                score += weight * 0.7
            elif 'Large' in row['size_category']:
                score += weight * 1.0
            else:  # Very Large
                score += weight * 0.8  # Diminishing returns
        
        return round(score * 100, 1)
    
    def _calculate_market_saturation(self, crop_data) -> float:
        """Calculate market saturation score for a crop"""
        # Simplified saturation calculation based on area
        area = crop_data['total_area']
        farm_count = crop_data['farm_count']
        
        # Mock market capacity (in real implementation, this would come from market data)
        market_capacities = {
            'wheat': 50000,
            'cotton': 30000,
            'potato': 20000
        }
        
        capacity = market_capacities.get(crop_data['crop_type'], 25000)
        saturation = min(area / capacity, 1.0)
        
        return round(saturation, 3)
    
    def _get_market_status(self, saturation_score: float) -> str:
        """Get market status based on saturation score"""
        if saturation_score < 0.3:
            return 'Undersupplied'
        elif saturation_score < 0.7:
            return 'Balanced'
        elif saturation_score < 0.9:
            return 'Near Saturation'
        else:
            return 'Oversaturated'
    
    def _calculate_market_balance(self, supply_data) -> Dict[str, Any]:
        """Calculate overall market balance"""
        total_area = sum(row['total_area'] for row in supply_data)
        crop_count = len(supply_data)
        
        return {
            'total_supply_area': round(total_area, 2),
            'crop_diversity': crop_count,
            'balance_score': min(crop_count / 5.0, 1.0),  # Optimal diversity around 5 crops
            'status': 'Diverse' if crop_count >= 4 else 'Limited Diversity'
        }
    
    def _generate_market_recommendations(self, indicators) -> List[str]:
        """Generate market-based recommendations"""
        recommendations = []
        
        for indicator in indicators:
            status = indicator['market_status']
            crop = indicator['crop_type']
            
            if status == 'Undersupplied':
                recommendations.append(f"Consider increasing {crop} production - market opportunity")
            elif status == 'Oversaturated':
                recommendations.append(f"Reduce {crop} planting - market oversupply risk")
        
        return recommendations
    
    def _calculate_sustainability_score(self, rotation_data) -> float:
        """Calculate sustainability score based on crop rotation"""
        if not rotation_data:
            return 0.0
        
        # Group by location
        locations = defaultdict(list)
        for row in rotation_data:
            location_key = (row['lat'], row['lng'])
            locations[location_key].append(row)
        
        rotation_scores = []
        for location, crops in locations.items():
            if len(crops) > 1:
                crop_types = [crop['crop_type'] for crop in crops]
                unique_crops = len(set(crop_types))
                rotation_score = min(unique_crops / 3.0, 1.0)  # Optimal rotation uses 3+ crops
                rotation_scores.append(rotation_score)
        
        if not rotation_scores:
            return 0.5  # Neutral score if no rotation data
        
        return round(np.mean(rotation_scores) * 100, 1)
    
    def _analyze_crop_rotation(self, rotation_data) -> Dict[str, Any]:
        """Analyze crop rotation patterns"""
        if not rotation_data:
            return {'rotation_frequency': 0, 'monoculture_risk': 'Unknown'}
        
        locations = defaultdict(list)
        for row in rotation_data:
            location_key = (row['lat'], row['lng'])
            locations[location_key].append(row['crop_type'])
        
        monoculture_count = sum(1 for crops in locations.values() if len(set(crops)) == 1)
        total_locations = len(locations)
        
        monoculture_ratio = monoculture_count / total_locations if total_locations > 0 else 0
        
        return {
            'rotation_frequency': round((1 - monoculture_ratio) * 100, 1),
            'monoculture_risk': 'High' if monoculture_ratio > 0.7 else 'Medium' if monoculture_ratio > 0.4 else 'Low',
            'locations_with_rotation': total_locations - monoculture_count
        }
    
    def _assess_environmental_impact(self, rotation_data) -> Dict[str, Any]:
        """Assess environmental impact"""
        return {
            'soil_health_risk': 'Medium',  # Simplified assessment
            'biodiversity_score': 7.5,
            'water_usage_efficiency': 'Good',
            'carbon_footprint': 'Moderate'
        }
    
    def _generate_sustainability_recommendations(self, score: float) -> List[str]:
        """Generate sustainability recommendations"""
        recommendations = []
        
        if score < 50:
            recommendations.extend([
                "Implement crop rotation to improve soil health",
                "Diversify crop selection to reduce disease risk",
                "Consider intercropping techniques"
            ])
        elif score < 75:
            recommendations.extend([
                "Continue current rotation practices",
                "Explore cover crops during fallow periods",
                "Monitor soil health indicators"
            ])
        else:
            recommendations.extend([
                "Excellent sustainability practices",
                "Share knowledge with neighboring farmers",
                "Consider precision agriculture techniques"
            ])
        
        return recommendations
    
    def _get_mock_dashboard_data(self) -> Dict[str, Any]:
        """Provide mock data when database is unavailable"""
        return {
            'basic_stats': {
                'total_reports': 150,
                'total_area': 2500.5,
                'crop_distribution': [
                    {'crop_type': 'wheat', 'count': 60, 'total_area': 1200.0},
                    {'crop_type': 'cotton', 'count': 45, 'total_area': 800.0},
                    {'crop_type': 'potato', 'count': 45, 'total_area': 500.5}
                ],
                'recent_reports': 25,
                'recent_area': 420.0,
                'avg_field_size': 16.67
            },
            'diversity_analysis': {
                'diversity_index': 1.045,
                'crop_count': 3,
                'area_distribution': [
                    {'crop_type': 'wheat', 'total_area': 1200.0, 'avg_size': 20.0},
                    {'crop_type': 'cotton', 'total_area': 800.0, 'avg_size': 17.8},
                    {'crop_type': 'potato', 'total_area': 500.5, 'avg_size': 11.1}
                ],
                'concentration_metrics': {'gini_coefficient': 0.234, 'herfindahl_index': 0.398}
            },
            'temporal_trends': {
                'monthly_trends': [],
                'seasonal_patterns': [],
                'growth_rate': 12.5
            },
            'geographic_data': {
                'regional_clusters': [],
                'density_analysis': {'avg_density': 2.3, 'max_density': 8, 'density_distribution': {'low': 80, 'medium': 50, 'high': 20}},
                'geographic_spread': {'lat_range': 2.5, 'lng_range': 3.2, 'coverage_area': 8.0}
            },
            'efficiency_analysis': {
                'size_efficiency': [],
                'optimization_opportunities': [
                    {'crop_type': 'potato', 'opportunity': 'Farm consolidation', 'potential_improvement': 'Increase efficiency through larger field sizes', 'priority': 'High'}
                ],
                'efficiency_score': 72.3
            },
            'market_indicators': {
                'supply_indicators': [
                    {'crop_type': 'wheat', 'supply_area': 1200.0, 'farm_count': 60, 'saturation_score': 0.024, 'market_status': 'Undersupplied'},
                    {'crop_type': 'cotton', 'supply_area': 800.0, 'farm_count': 45, 'saturation_score': 0.027, 'market_status': 'Undersupplied'},
                    {'crop_type': 'potato', 'supply_area': 500.5, 'farm_count': 45, 'saturation_score': 0.025, 'market_status': 'Undersupplied'}
                ],
                'market_balance': {'total_supply_area': 2500.5, 'crop_diversity': 3, 'balance_score': 0.6, 'status': 'Limited Diversity'},
                'recommendations': ['Consider increasing wheat production - market opportunity', 'Consider increasing cotton production - market opportunity', 'Consider increasing potato production - market opportunity']
            },
            'sustainability_metrics': {
                'sustainability_score': 65.0,
                'rotation_analysis': {'rotation_frequency': 35.0, 'monoculture_risk': 'Medium', 'locations_with_rotation': 52},
                'environmental_impact': {'soil_health_risk': 'Medium', 'biodiversity_score': 7.5, 'water_usage_efficiency': 'Good', 'carbon_footprint': 'Moderate'},
                'recommendations': ['Continue current rotation practices', 'Explore cover crops during fallow periods', 'Monitor soil health indicators']
            },
            'generated_at': datetime.now().isoformat()
        }

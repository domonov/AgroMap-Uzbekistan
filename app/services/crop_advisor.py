class CropAdvisor:
    def __init__(self):
        self.rotation_rules = {
            'wheat': ['cotton', 'potato'],
            'cotton': ['wheat'],
            'potato': ['wheat', 'cotton']
        }
        
        self.incompatible_crops = {
            'wheat': ['wheat'],
            'cotton': ['cotton'],
            'potato': ['potato']
        }
        
        # Optimal planting times (month ranges)
        self.planting_calendar = {
            'wheat': {'start_month': 9, 'end_month': 11},  # Sept to Nov
            'cotton': {'start_month': 3, 'end_month': 5},  # March to May
            'potato': {'start_month': 2, 'end_month': 4},  # Feb to April
        }
    
    def get_rotation_suggestions(self, previous_crop):
        """Get crop rotation suggestions based on previous crop"""
        if not previous_crop:
            return list(self.rotation_rules.keys())
        
        return self.rotation_rules.get(previous_crop, [])
    
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
"""API optimization utilities."""
import time
from functools import wraps
from typing import Dict, List, Any, Callable
from flask import request, current_app, g, Response
import logging
from cachelib import SimpleCache

logger = logging.getLogger(__name__)
cache = SimpleCache()

class APIOptimizer:
    def __init__(self, app=None):
        self.app = app
        self.performance_data: Dict[str, List[float]] = {}
        self.slow_threshold = 500  # ms
        
        if app is not None:
            self.init_app(app)
    
    def init_app(self, app):
        """Initialize with Flask app."""
        self.app = app
        
        @app.before_request
        def before_request():
            g.start_time = time.time()
        
        @app.after_request
        def after_request(response):
            if request.endpoint:
                total_time = (time.time() - g.start_time) * 1000
                endpoint = request.endpoint
                
                if endpoint not in self.performance_data:
                    self.performance_data[endpoint] = []
                
                self.performance_data[endpoint].append(total_time)
                
                # Log slow endpoints
                if total_time > self.slow_threshold:
                    logger.warning(f"Slow API endpoint: {endpoint} took {total_time:.2f}ms")
                
                # Add Server-Timing header
                response.headers['Server-Timing'] = f'total;dur={total_time:.2f}'
            
            return response
    
    def cache_response(self, timeout: int = 300) -> Callable:
        """Cache API response decorator."""
        def decorator(f: Callable) -> Callable:
            @wraps(f)
            def decorated_function(*args, **kwargs):
                # Generate cache key
                cache_key = f"{request.path}:{request.query_string.decode()}"
                
                # Try to get from cache
                rv = cache.get(cache_key)
                if rv is not None:
                    return rv
                
                # If not in cache, generate response
                rv = f(*args, **kwargs)
                
                # Cache the response
                cache.set(cache_key, rv, timeout=timeout)
                return rv
            return decorated_function
        return decorator
    
    def rate_limit(self, limit: int = 100, period: int = 60) -> Callable:
        """Rate limiting decorator."""
        def decorator(f: Callable) -> Callable:
            @wraps(f)
            def decorated_function(*args, **kwargs):
                # Get client identifier (IP or API key)
                client_id = request.headers.get('X-API-Key') or request.remote_addr
                
                # Generate rate limit key
                rate_key = f"rate:{client_id}:{request.endpoint}"
                
                # Get current count
                count = cache.get(rate_key) or 0
                
                if count >= limit:
                    return {'error': 'Rate limit exceeded'}, 429
                
                # Increment count
                cache.set(rate_key, count + 1, timeout=period)
                
                # Add rate limit headers
                response = f(*args, **kwargs)
                if isinstance(response, tuple):
                    response_obj, code = response
                else:
                    response_obj, code = response, 200
                
                headers = {
                    'X-RateLimit-Limit': str(limit),
                    'X-RateLimit-Remaining': str(limit - count - 1),
                    'X-RateLimit-Reset': str(int(time.time()) + period)
                }
                
                return response_obj, code, headers
            return decorated_function
        return decorator
    
    def optimize_query_params(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Optimize API query parameters."""
        optimized = {}
        
        # Handle pagination
        page = int(params.get('page', 1))
        per_page = int(params.get('per_page', 20))
        per_page = min(per_page, 100)  # Limit max items per page
        optimized.update({'page': page, 'per_page': per_page})
        
        # Handle filtering
        filters = params.get('filters', {})
        if filters:
            # Remove empty filters
            filters = {k: v for k, v in filters.items() if v is not None and v != ''}
            optimized['filters'] = filters
        
        # Handle sorting
        sort = params.get('sort')
        if sort:
            # Validate sort field
            if sort.lstrip('-') in self.valid_sort_fields():
                optimized['sort'] = sort
        
        # Handle field selection
        fields = params.get('fields')
        if fields:
            # Validate requested fields
            valid_fields = set(self.valid_fields())
            requested_fields = set(fields.split(','))
            optimized['fields'] = ','.join(valid_fields & requested_fields)
        
        return optimized
    
    def compress_response(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Compress API response data."""
        if isinstance(data, dict):
            # Remove null values
            data = {k: v for k, v in data.items() if v is not None}
            
            # Compress nested objects
            for k, v in data.items():
                if isinstance(v, (dict, list)):
                    data[k] = self.compress_response(v)
        
        elif isinstance(data, list):
            # Compress list items
            data = [self.compress_response(item) if isinstance(item, (dict, list)) else item 
                   for item in data]
        
        return data
    
    def get_endpoint_stats(self) -> Dict[str, Dict[str, float]]:
        """Get performance stats for all endpoints."""
        stats = {}
        for endpoint, times in self.performance_data.items():
            if times:
                avg_time = sum(times) / len(times)
                max_time = max(times)
                min_time = min(times)
                
                stats[endpoint] = {
                    'avg_time': avg_time,
                    'max_time': max_time,
                    'min_time': min_time,
                    'call_count': len(times)
                }
        return stats
    
    @staticmethod
    def valid_sort_fields() -> List[str]:
        """Get list of valid sort fields."""
        return ['id', 'created_at', 'updated_at', 'name']
    
    @staticmethod
    def valid_fields() -> List[str]:
        """Get list of valid fields for selection."""
        return ['id', 'name', 'description', 'created_at', 'updated_at']
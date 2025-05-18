"""
Caching middleware for AgroMap Uzbekistan
Implements server-side caching to improve performance
"""

import functools
import hashlib
import json
import os
import time
from datetime import datetime, timedelta
from flask import request, Response, current_app
from cachelib import SimpleCache, FileSystemCache, MemcachedCache

# Initialize cache based on configuration
def init_cache(app):
    """Initialize the appropriate cache based on app configuration"""
    cache_type = app.config.get('CACHE_TYPE', 'simple')

    if cache_type == 'simple':
        return SimpleCache(
            threshold=app.config.get('CACHE_THRESHOLD', 500),
            default_timeout=app.config.get('CACHE_DEFAULT_TIMEOUT', 300)
        )
    elif cache_type == 'filesystem':
        cache_dir = app.config.get('CACHE_DIR', os.path.join(app.instance_path, 'cache'))
        if not os.path.exists(cache_dir):
            os.makedirs(cache_dir)
        return FileSystemCache(
            cache_dir=cache_dir,
            threshold=app.config.get('CACHE_THRESHOLD', 500),
            default_timeout=app.config.get('CACHE_DEFAULT_TIMEOUT', 300)
        )
    elif cache_type == 'memcached':
        servers = app.config.get('CACHE_MEMCACHED_SERVERS', ['127.0.0.1:11211'])
        return MemcachedCache(
            servers=servers,
            default_timeout=app.config.get('CACHE_DEFAULT_TIMEOUT', 300)
        )
    else:
        # Default to simple cache
        return SimpleCache()

# Create a cache key from the request
def make_cache_key():
    """Create a unique cache key based on the request"""
    # Start with the path
    key_parts = [request.path]

    # Add query parameters, sorted for consistency
    args = request.args.copy()
    if args:
        key_parts.append('?')
        key_parts.append('&'.join(sorted([
            f"{k}={v}" for k, v in args.items()
        ])))

    # Add request method if not GET
    if request.method != 'GET':
        key_parts.append(f"#{request.method}")

    # Add user ID if authenticated and personalized caching is enabled
    if hasattr(request, 'user') and request.user and request.user.is_authenticated:
        if current_app.config.get('CACHE_PERSONALIZED', False):
            key_parts.append(f"@{request.user.id}")

    # Create a hash of the key parts
    key = ''.join(key_parts)
    return hashlib.md5(key.encode('utf-8')).hexdigest()

# Cache decorator for routes
def cached(timeout=None, key_prefix='', unless=None):
    """
    Decorator to cache view functions

    Args:
        timeout: Cache timeout in seconds (default: use CACHE_DEFAULT_TIMEOUT)
        key_prefix: Prefix for cache key
        unless: Function that returns True if caching should be bypassed
    """
    def decorator(f):
        @functools.wraps(f)
        def decorated_function(*args, **kwargs):
            # Check if caching should be bypassed
            if callable(unless) and unless():
                return f(*args, **kwargs)

            # Get cache from app context
            cache = current_app.extensions.get('cache')
            if not cache:
                return f(*args, **kwargs)

            # Create cache key
            cache_key = key_prefix + make_cache_key()

            # Try to get response from cache
            rv = cache.get(cache_key)
            if rv:
                # Return cached response
                return Response(
                    rv[0],
                    status=rv[1],
                    headers=rv[2],
                    mimetype=rv[3]
                )

            # Call the view function
            response = f(*args, **kwargs)

            # Cache the response if it's cacheable
            if response.status_code == 200 and request.method == 'GET':
                cache_timeout = timeout or current_app.config.get('CACHE_DEFAULT_TIMEOUT', 300)
                cache.set(
                    cache_key,
                    (response.get_data(), response.status_code, dict(response.headers), response.mimetype),
                    timeout=cache_timeout
                )

            return response
        return decorated_function
    return decorator

# Cache invalidation
def invalidate_cache(pattern=None):
    """
    Invalidate cache entries matching the pattern

    Args:
        pattern: Pattern to match cache keys (None to invalidate all)
    """
    cache = current_app.extensions.get('cache')
    if not cache:
        return

    # For SimpleCache, we can only clear all
    if isinstance(cache, SimpleCache):
        cache.clear()
        return

    # For other cache types, try to delete by pattern if supported
    if hasattr(cache, 'delete_many') and pattern:
        keys = [k for k in cache.keys() if pattern in k]
        if keys:
            cache.delete_many(keys)
    else:
        # Fallback to clearing all
        cache.clear()

# Cache middleware
class CacheMiddleware:
    """Middleware to add cache headers to responses"""

    def __init__(self, app=None):
        self.app = app
        if app is not None:
            self.init_app(app)

    def init_app(self, app):
        """Initialize the middleware with the Flask app"""
        app.after_request(self.add_cache_headers)

        # Initialize cache and add to app extensions
        cache = init_cache(app)
        app.extensions['cache'] = cache

    def add_cache_headers(self, response):
        """Add appropriate cache headers to the response"""
        # Skip if not cacheable
        if request.method != 'GET' or response.status_code != 200:
            return response

        # Get cache settings from config
        browser_cache = current_app.config.get('BROWSER_CACHE_ENABLED', True)
        max_age = current_app.config.get('BROWSER_CACHE_MAX_AGE', 3600)  # 1 hour default

        # Add cache headers if enabled
        if browser_cache:
            # Check if path should be cached
            path = request.path

            # Skip API endpoints and dynamic content
            if path.startswith('/api/') or path.startswith('/dashboard/'):
                response.headers['Cache-Control'] = 'no-store, no-cache, must-revalidate, max-age=0'
                return response

            # Cache static assets longer
            if path.startswith('/static/'):
                # Set longer cache for static assets
                response.headers['Cache-Control'] = f'public, max-age={max_age * 24}'  # 1 day
                response.headers['Expires'] = (datetime.utcnow() + timedelta(seconds=max_age * 24)).strftime(
                    '%a, %d %b %Y %H:%M:%S GMT')
            else:
                # Set standard cache for other content
                response.headers['Cache-Control'] = f'public, max-age={max_age}'
                response.headers['Expires'] = (datetime.utcnow() + timedelta(seconds=max_age)).strftime(
                    '%a, %d %b %Y %H:%M:%S GMT')

            # Add ETag for validation
            content = response.get_data()
            if content:
                etag = hashlib.md5(content).hexdigest()
                response.headers['ETag'] = f'"{etag}"'

        return response

# Function to warm up the cache with frequently accessed pages
def warm_cache(app, urls=None):
    """
    Pre-populate the cache with frequently accessed pages

    Args:
        app: Flask app
        urls: List of URLs to cache (default: use CACHE_WARMUP_URLS from config)
    """
    with app.test_client() as client:
        urls = urls or app.config.get('CACHE_WARMUP_URLS', [])
        for url in urls:
            client.get(url)
            app.logger.info(f"Warmed up cache for {url}")

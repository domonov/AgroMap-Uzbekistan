"""Web performance optimization utilities for AgroMap."""
import os
import gzip
import brotli
from PIL import Image
from io import BytesIO
import urllib.parse
from functools import lru_cache
from flask import request, current_app
from app.utils.image_optimizer import optimize_image, create_responsive_images
from app.utils.js_optimizer import JSOptimizer

class PerformanceOptimizer:
    def __init__(self, app=None):
        self.app = app
        if app is not None:
            self.init_app(app)

    def init_app(self, app):
        """Initialize the optimizer with the Flask app."""
        self.app = app
        self.js_optimizer = JSOptimizer(
            static_dir=os.path.join(app.root_path, 'static'),
            development=app.debug
        )

        # Add compression headers
        @app.after_request
        def add_compression_headers(response):
            return self.compress_response(response)

        # Add cache headers
        @app.after_request
        def add_cache_headers(response):
            return self.add_cache_control(response)

        # Add performance headers
        @app.after_request
        def add_performance_headers(response):
            headers = self.get_performance_headers()
            for key, value in headers.items():
                response.headers[key] = value
            return response

    def compress_response(self, response):
        """Compress response data if supported by the client."""
        accept_encoding = request.headers.get('Accept-Encoding', '')

        if not response.direct_passthrough:
            if 'br' in accept_encoding and len(response.data) > 500:
                # Use Brotli compression
                response.data = brotli.compress(response.data)
                response.headers['Content-Encoding'] = 'br'
            elif 'gzip' in accept_encoding and len(response.data) > 500:
                # Fallback to gzip
                response.data = gzip.compress(response.data)
                response.headers['Content-Encoding'] = 'gzip'

        return response

    def add_cache_control(self, response):
        """Add appropriate cache control headers."""
        if request.method == 'GET' and response.status_code == 200:
            url = URL(request.url)  # Updated from url_parse
            path = url.path

            # Static assets
            if path.startswith('/static/'):
                if '.bundle.' in path or '.min.' in path:
                    # Bundled/minified assets - cache for 1 year
                    response.headers['Cache-Control'] = 'public, max-age=31536000'
                else:
                    # Regular static files - cache for 1 week
                    response.headers['Cache-Control'] = 'public, max-age=604800'

            # API responses
            elif path.startswith('/api/'):
                # Cache API responses for 5 minutes
                response.headers['Cache-Control'] = 'private, max-age=300'

            else:
                # Default - no cache for dynamic content
                response.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate'

        return response

    @lru_cache(maxsize=100)
    def optimize_static_file(self, filepath):
        """Optimize a static file based on its type."""
        ext = os.path.splitext(filepath)[1].lower()

        if ext in ['.js']:
            return self.js_optimizer.optimize_file(filepath)
        elif ext in ['.jpg', '.jpeg', '.png', '.webp']:
            return optimize_image(filepath)
        
        return filepath

    def create_srcset(self, image_path, widths=[320, 640, 960, 1280]):
        """Create srcset for responsive images."""
        try:
            dir_path = os.path.dirname(image_path)
            name = os.path.splitext(os.path.basename(image_path))[0]
            srcset = []

            for width in widths:
                optimized = optimize_image(
                    image_path,
                    output_path=os.path.join(dir_path, f"{name}-{width}.webp"),
                    max_size=width
                )
                if optimized:
                    srcset.append(f"{optimized} {width}w")

            return ", ".join(srcset)
        except Exception as e:
            current_app.logger.error(f"Error creating srcset for {image_path}: {e}")
            return ""

    def get_performance_headers(self):
        """Get recommended security and performance headers."""
        return {
            'X-Content-Type-Options': 'nosniff',
            'X-Frame-Options': 'SAMEORIGIN',
            'X-XSS-Protection': '1; mode=block',
            'Referrer-Policy': 'strict-origin-when-cross-origin',
            'Permissions-Policy': 'geolocation=(self), microphone=()',
            'Feature-Policy': 'camera none; microphone none; geolocation self',
            'Server-Timing': 'miss, db;dur=53, app;dur=47.2'
        }

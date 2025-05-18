"""Asset optimization utilities for AgroMap."""
import os
import subprocess
import json
from csscompressor import compress as compress_css
from jsmin import jsmin
from flask import url_for
from hashlib import md5

class AssetOptimizer:
    def __init__(self, app_static_dir, development=False):
        self.static_dir = app_static_dir
        self.development = development
        self.manifest = {}
        self.manifest_path = os.path.join(app_static_dir, 'manifest.json')
        
        # Load existing manifest if it exists
        if os.path.exists(self.manifest_path):
            with open(self.manifest_path, 'r') as f:
                self.manifest = json.load(f)
    
    def optimize_css(self, css_path):
        """Optimize a CSS file."""
        try:
            with open(css_path, 'r') as f:
                content = f.read()
            
            # Skip optimization in development mode
            if self.development:
                return content
            
            # Compress CSS
            compressed = compress_css(content)
            
            # Generate hash for cache busting
            content_hash = md5(compressed.encode()).hexdigest()[:8]
            
            # Save optimized file
            filename = os.path.basename(css_path)
            new_filename = f"{os.path.splitext(filename)[0]}.{content_hash}.min.css"
            output_path = os.path.join(os.path.dirname(css_path), new_filename)
            
            with open(output_path, 'w') as f:
                f.write(compressed)
            
            # Update manifest
            rel_path = os.path.relpath(css_path, self.static_dir)
            self.manifest[rel_path] = os.path.relpath(output_path, self.static_dir)
            return output_path
        except Exception as e:
            print(f"Error optimizing CSS {css_path}: {e}")
            return css_path
    
    def optimize_js(self, js_path):
        """Optimize a JavaScript file."""
        try:
            with open(js_path, 'r') as f:
                content = f.read()
            
            # Skip optimization in development mode
            if self.development:
                return content
            
            # Minify JavaScript
            minified = jsmin(content)
            
            # Generate hash for cache busting
            content_hash = md5(minified.encode()).hexdigest()[:8]
            
            # Save optimized file
            filename = os.path.basename(js_path)
            new_filename = f"{os.path.splitext(filename)[0]}.{content_hash}.min.js"
            output_path = os.path.join(os.path.dirname(js_path), new_filename)
            
            with open(output_path, 'w') as f:
                f.write(minified)
            
            # Update manifest
            rel_path = os.path.relpath(js_path, self.static_dir)
            self.manifest[rel_path] = os.path.relpath(output_path, self.static_dir)
            return output_path
        except Exception as e:
            print(f"Error optimizing JavaScript {js_path}: {e}")
            return js_path
    
    def optimize_all(self):
        """Optimize all CSS and JS files in the static directory."""
        try:
            # Process CSS files
            css_dir = os.path.join(self.static_dir, 'css')
            if os.path.exists(css_dir):
                for filename in os.listdir(css_dir):
                    if filename.endswith('.css') and not filename.endswith('.min.css'):
                        css_path = os.path.join(css_dir, filename)
                        self.optimize_css(css_path)
            
            # Process JavaScript files
            js_dir = os.path.join(self.static_dir, 'js')
            if os.path.exists(js_dir):
                for filename in os.listdir(js_dir):
                    if filename.endswith('.js') and not filename.endswith('.min.js'):
                        js_path = os.path.join(js_dir, filename)
                        self.optimize_js(js_path)
            
            # Save updated manifest
            with open(self.manifest_path, 'w') as f:
                json.dump(self.manifest, f, indent=2)
        except Exception as e:
            print(f"Error during asset optimization: {e}")
    
    def get_optimized_url(self, file_path):
        """Get the URL for an optimized asset."""
        try:
            rel_path = os.path.relpath(file_path, self.static_dir)
            if rel_path in self.manifest:
                return url_for('static', filename=self.manifest[rel_path])
            return url_for('static', filename=rel_path)
        except Exception as e:
            print(f"Error getting optimized URL for {file_path}: {e}")
            return file_path

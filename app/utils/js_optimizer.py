"""JavaScript optimization utilities for AgroMap."""
from jsmin import jsmin
import os
from hashlib import md5
import json

class JSOptimizer:
    def __init__(self, static_dir, development=False):
        self.static_dir = static_dir
        self.development = development
        self.manifest = {}
        self.manifest_path = os.path.join(static_dir, 'js', 'manifest.json')
        
        if os.path.exists(self.manifest_path):
            with open(self.manifest_path, 'r') as f:
                self.manifest = json.load(f)

    def optimize_file(self, js_path):
        """Optimize a single JavaScript file."""
        try:
            if not os.path.exists(js_path):
                raise FileNotFoundError(f"JavaScript file not found: {js_path}")

            # Skip optimization in development mode
            if self.development:
                return js_path

            with open(js_path, 'r', encoding='utf-8') as f:
                content = f.read()

            # Minify JavaScript
            minified = jsmin(content)

            # Generate hash for cache busting
            content_hash = md5(minified.encode()).hexdigest()[:8]

            # Create optimized filename
            filename = os.path.basename(js_path)
            new_filename = f"{os.path.splitext(filename)[0]}.{content_hash}.min.js"
            output_dir = os.path.join(self.static_dir, 'js', 'dist')
            os.makedirs(output_dir, exist_ok=True)
            output_path = os.path.join(output_dir, new_filename)

            # Save optimized file
            with open(output_path, 'w', encoding='utf-8') as f:
                f.write(minified)

            # Update manifest
            rel_path = os.path.relpath(js_path, self.static_dir)
            self.manifest[rel_path] = os.path.relpath(output_path, self.static_dir)
            
            with open(self.manifest_path, 'w') as f:
                json.dump(self.manifest, f, indent=2)

            return output_path
        except Exception as e:
            print(f"Error optimizing JavaScript file {js_path}: {e}")
            return js_path

    def create_bundle(self, files, output_name):
        """Create a bundle from multiple JavaScript files."""
        try:
            combined = []
            for file_path in files:
                full_path = os.path.join(self.static_dir, file_path)
                if os.path.exists(full_path):
                    with open(full_path, 'r', encoding='utf-8') as f:
                        content = f.read()
                        if not self.development:
                            content = jsmin(content)
                        combined.append(content)

            # Combine all files
            bundle_content = '\n'.join(combined)
            
            # Generate hash for cache busting
            content_hash = md5(bundle_content.encode()).hexdigest()[:8]
            
            # Create bundle filename
            bundle_filename = f"{output_name}.{content_hash}.bundle.min.js"
            output_dir = os.path.join(self.static_dir, 'js', 'dist')
            os.makedirs(output_dir, exist_ok=True)
            output_path = os.path.join(output_dir, bundle_filename)

            # Save bundle
            with open(output_path, 'w', encoding='utf-8') as f:
                f.write(bundle_content)

            # Update manifest
            bundle_key = f"bundles/{output_name}"
            self.manifest[bundle_key] = os.path.relpath(output_path, self.static_dir)
            
            with open(self.manifest_path, 'w') as f:
                json.dump(self.manifest, f, indent=2)

            return output_path
        except Exception as e:
            print(f"Error creating JavaScript bundle: {e}")
            return None

    def get_optimized_path(self, js_path):
        """Get the path to the optimized version of a JavaScript file."""
        try:
            rel_path = os.path.relpath(js_path, self.static_dir)
            return self.manifest.get(rel_path, js_path)
        except Exception as e:
            print(f"Error getting optimized path for {js_path}: {e}")
            return js_path

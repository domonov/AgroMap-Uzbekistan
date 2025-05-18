"""Final optimization utilities for AgroMap."""
import os
import re
import json
import logging
import subprocess
import time
from typing import Dict, List, Optional, Any, Union
from flask import Flask, current_app
from PIL import Image
import cssmin
import jsmin
import htmlmin
from sqlalchemy import text

# Set up logger
logger = logging.getLogger('optimization')
handler = logging.FileHandler('logs/optimization.log')
handler.setFormatter(logging.Formatter(
    '%(asctime)s - %(levelname)s - %(message)s'
))
logger.addHandler(handler)
logger.setLevel(logging.INFO)

class FinalOptimizer:
    """Final optimization for AgroMap."""
    
    def __init__(self, app: Optional[Flask] = None, db=None):
        self.app = app
        self.db = db
        self.static_dir = 'app/static'
        self.templates_dir = 'app/templates'
        self.reports_dir = 'data/optimization/reports'
        
        # Create directories if they don't exist
        os.makedirs(self.reports_dir, exist_ok=True)
        os.makedirs('logs', exist_ok=True)
        
        if app is not None:
            self.init_app(app, db)
    
    def init_app(self, app: Flask, db=None):
        """Initialize with Flask app."""
        self.app = app
        self.db = db
        
        # Register commands
        @app.cli.command("optimize-images")
        def optimize_images_command():
            """Optimize images."""
            results = self.optimize_images()
            print(f"Optimized {results['optimized']} images, saved {results['bytes_saved']} bytes")
        
        @app.cli.command("minimize-assets")
        def minimize_assets_command():
            """Minimize CSS, JS, and HTML assets."""
            results = self.minimize_assets()
            print(f"Minimized {results['minimized']} assets, saved {results['bytes_saved']} bytes")
        
        @app.cli.command("optimize-cache")
        def optimize_cache_command():
            """Optimize cache settings."""
            results = self.optimize_cache()
            print(f"Optimized cache settings for {results['optimized']} resources")
        
        @app.cli.command("tune-database")
        def tune_database_command():
            """Tune database performance."""
            results = self.tune_database()
            print(f"Applied {results['optimizations']} database optimizations")
        
        @app.cli.command("optimize-api")
        def optimize_api_command():
            """Optimize API performance."""
            results = self.optimize_api()
            print(f"Applied {results['optimizations']} API optimizations")
        
        @app.cli.command("cleanup-code")
        def cleanup_code_command():
            """Clean up code."""
            results = self.cleanup_code()
            print(f"Cleaned up {results['files']} files, removed {results['lines']} lines of dead code")
        
        @app.cli.command("run-all-optimizations")
        def run_all_optimizations_command():
            """Run all optimizations."""
            self.run_all_optimizations()
            print("All optimizations completed")
    
    def optimize_images(self) -> Dict:
        """Optimize images in static directory."""
        logger.info("Optimizing images")
        
        results = {
            'optimized': 0,
            'bytes_saved': 0,
            'details': []
        }
        
        # Find all image files
        for root, _, files in os.walk(self.static_dir):
            for file in files:
                if file.lower().endswith(('.jpg', '.jpeg', '.png', '.gif', '.webp')):
                    file_path = os.path.join(root, file)
                    
                    try:
                        # Get original file size
                        original_size = os.path.getsize(file_path)
                        
                        # Optimize image
                        if file.lower().endswith(('.jpg', '.jpeg')):
                            self._optimize_jpeg(file_path)
                        elif file.lower().endswith('.png'):
                            self._optimize_png(file_path)
                        elif file.lower().endswith('.gif'):
                            self._optimize_gif(file_path)
                        elif file.lower().endswith('.webp'):
                            self._optimize_webp(file_path)
                        
                        # Get new file size
                        new_size = os.path.getsize(file_path)
                        bytes_saved = original_size - new_size
                        
                        if bytes_saved > 0:
                            results['optimized'] += 1
                            results['bytes_saved'] += bytes_saved
                            results['details'].append({
                                'file': file_path,
                                'original_size': original_size,
                                'new_size': new_size,
                                'bytes_saved': bytes_saved,
                                'percent_saved': round((bytes_saved / original_size) * 100, 2)
                            })
                            
                            logger.info(f"Optimized {file_path}: saved {bytes_saved} bytes ({results['details'][-1]['percent_saved']}%)")
                    
                    except Exception as e:
                        logger.error(f"Error optimizing {file_path}: {str(e)}")
        
        # Save results to file
        self._save_optimization_results('image_optimization', results)
        
        return results
    
    def _optimize_jpeg(self, file_path: str) -> None:
        """Optimize JPEG image."""
        try:
            # Open image
            img = Image.open(file_path)
            
            # Save with optimized settings
            img.save(file_path, 'JPEG', quality=85, optimize=True, progressive=True)
        except Exception as e:
            logger.error(f"Error optimizing JPEG {file_path}: {str(e)}")
            raise
    
    def _optimize_png(self, file_path: str) -> None:
        """Optimize PNG image."""
        try:
            # Try to use optipng if available
            try:
                subprocess.run(['optipng', '-quiet', '-o2', file_path], check=True)
            except (subprocess.SubprocessError, FileNotFoundError):
                # Fall back to PIL
                img = Image.open(file_path)
                img.save(file_path, 'PNG', optimize=True)
        except Exception as e:
            logger.error(f"Error optimizing PNG {file_path}: {str(e)}")
            raise
    
    def _optimize_gif(self, file_path: str) -> None:
        """Optimize GIF image."""
        try:
            # Open image
            img = Image.open(file_path)
            
            # Save with optimized settings
            img.save(file_path, 'GIF', optimize=True)
        except Exception as e:
            logger.error(f"Error optimizing GIF {file_path}: {str(e)}")
            raise
    
    def _optimize_webp(self, file_path: str) -> None:
        """Optimize WebP image."""
        try:
            # Open image
            img = Image.open(file_path)
            
            # Save with optimized settings
            img.save(file_path, 'WEBP', quality=85, method=6)
        except Exception as e:
            logger.error(f"Error optimizing WebP {file_path}: {str(e)}")
            raise
    
    def minimize_assets(self) -> Dict:
        """Minimize CSS, JS, and HTML assets."""
        logger.info("Minimizing assets")
        
        results = {
            'minimized': 0,
            'bytes_saved': 0,
            'details': []
        }
        
        # Minimize CSS files
        for root, _, files in os.walk(self.static_dir):
            for file in files:
                if file.lower().endswith('.css') and not file.lower().endswith('.min.css'):
                    file_path = os.path.join(root, file)
                    
                    try:
                        # Get original file size
                        original_size = os.path.getsize(file_path)
                        
                        # Minimize CSS
                        with open(file_path, 'r', encoding='utf-8') as f:
                            content = f.read()
                        
                        minimized = cssmin.cssmin(content)
                        
                        # Write minimized content
                        with open(file_path, 'w', encoding='utf-8') as f:
                            f.write(minimized)
                        
                        # Get new file size
                        new_size = os.path.getsize(file_path)
                        bytes_saved = original_size - new_size
                        
                        if bytes_saved > 0:
                            results['minimized'] += 1
                            results['bytes_saved'] += bytes_saved
                            results['details'].append({
                                'file': file_path,
                                'type': 'CSS',
                                'original_size': original_size,
                                'new_size': new_size,
                                'bytes_saved': bytes_saved,
                                'percent_saved': round((bytes_saved / original_size) * 100, 2)
                            })
                            
                            logger.info(f"Minimized CSS {file_path}: saved {bytes_saved} bytes ({results['details'][-1]['percent_saved']}%)")
                    
                    except Exception as e:
                        logger.error(f"Error minimizing CSS {file_path}: {str(e)}")
        
        # Minimize JS files
        for root, _, files in os.walk(self.static_dir):
            for file in files:
                if file.lower().endswith('.js') and not file.lower().endswith('.min.js'):
                    file_path = os.path.join(root, file)
                    
                    try:
                        # Get original file size
                        original_size = os.path.getsize(file_path)
                        
                        # Minimize JS
                        with open(file_path, 'r', encoding='utf-8') as f:
                            content = f.read()
                        
                        minimized = jsmin.jsmin(content)
                        
                        # Write minimized content
                        with open(file_path, 'w', encoding='utf-8') as f:
                            f.write(minimized)
                        
                        # Get new file size
                        new_size = os.path.getsize(file_path)
                        bytes_saved = original_size - new_size
                        
                        if bytes_saved > 0:
                            results['minimized'] += 1
                            results['bytes_saved'] += bytes_saved
                            results['details'].append({
                                'file': file_path,
                                'type': 'JS',
                                'original_size': original_size,
                                'new_size': new_size,
                                'bytes_saved': bytes_saved,
                                'percent_saved': round((bytes_saved / original_size) * 100, 2)
                            })
                            
                            logger.info(f"Minimized JS {file_path}: saved {bytes_saved} bytes ({results['details'][-1]['percent_saved']}%)")
                    
                    except Exception as e:
                        logger.error(f"Error minimizing JS {file_path}: {str(e)}")
        
        # Minimize HTML files
        for root, _, files in os.walk(self.templates_dir):
            for file in files:
                if file.lower().endswith('.html'):
                    file_path = os.path.join(root, file)
                    
                    try:
                        # Get original file size
                        original_size = os.path.getsize(file_path)
                        
                        # Minimize HTML
                        with open(file_path, 'r', encoding='utf-8') as f:
                            content = f.read()
                        
                        minimized = htmlmin.minify(content, remove_comments=True, remove_empty_space=True)
                        
                        # Write minimized content
                        with open(file_path, 'w', encoding='utf-8') as f:
                            f.write(minimized)
                        
                        # Get new file size
                        new_size = os.path.getsize(file_path)
                        bytes_saved = original_size - new_size
                        
                        if bytes_saved > 0:
                            results['minimized'] += 1
                            results['bytes_saved'] += bytes_saved
                            results['details'].append({
                                'file': file_path,
                                'type': 'HTML',
                                'original_size': original_size,
                                'new_size': new_size,
                                'bytes_saved': bytes_saved,
                                'percent_saved': round((bytes_saved / original_size) * 100, 2)
                            })
                            
                            logger.info(f"Minimized HTML {file_path}: saved {bytes_saved} bytes ({results['details'][-1]['percent_saved']}%)")
                    
                    except Exception as e:
                        logger.error(f"Error minimizing HTML {file_path}: {str(e)}")
        
        # Save results to file
        self._save_optimization_results('asset_minimization', results)
        
        return results
    
    def optimize_cache(self) -> Dict:
        """Optimize cache settings."""
        logger.info("Optimizing cache settings")
        
        results = {
            'optimized': 0,
            'details': []
        }
        
        # Update Flask cache settings
        if self.app:
            # Set longer cache times for static assets
            self.app.config['SEND_FILE_MAX_AGE_DEFAULT'] = 31536000  # 1 year
            results['optimized'] += 1
            results['details'].append({
                'type': 'Flask config',
                'setting': 'SEND_FILE_MAX_AGE_DEFAULT',
                'value': '31536000 (1 year)'
            })
            
            logger.info("Updated Flask cache settings")
        
        # Update cache headers in after_request handler
        if self.app:
            @self.app.after_request
            def add_cache_headers(response):
                # Skip if this is already handled elsewhere
                if 'Cache-Control' in response.headers:
                    return response
                
                # Add cache headers based on content type
                if request.path.startswith('/static/'):
                    if any(request.path.endswith(ext) for ext in ['.css', '.js', '.jpg', '.jpeg', '.png', '.gif', '.webp']):
                        response.headers['Cache-Control'] = 'public, max-age=31536000'  # 1 year
                    else:
                        response.headers['Cache-Control'] = 'public, max-age=86400'  # 1 day
                elif request.path.startswith('/api/'):
                    response.headers['Cache-Control'] = 'private, max-age=60'  # 1 minute
                else:
                    response.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate'
                
                return response
            
            results['optimized'] += 1
            results['details'].append({
                'type': 'HTTP headers',
                'setting': 'Cache-Control',
                'value': 'Optimized based on content type'
            })
            
            logger.info("Added cache headers to responses")
        
        # Save results to file
        self._save_optimization_results('cache_optimization', results)
        
        return results
    
    def tune_database(self) -> Dict:
        """Tune database performance."""
        logger.info("Tuning database performance")
        
        results = {
            'optimizations': 0,
            'details': []
        }
        
        if not self.db:
            logger.warning("Database not available for tuning")
            return results
        
        try:
            # Check if we're using PostgreSQL
            db_uri = self.app.config.get('SQLALCHEMY_DATABASE_URI', '')
            if 'postgresql' in db_uri:
                # Add indexes to commonly queried columns
                with self.db.engine.connect() as conn:
                    # Get all tables
                    tables = conn.execute(text("SELECT tablename FROM pg_tables WHERE schemaname = 'public'"))
                    
                    for table in tables:
                        table_name = table[0]
                        
                        # Add index to created_at columns if they exist
                        try:
                            conn.execute(text(f"CREATE INDEX IF NOT EXISTS idx_{table_name}_created_at ON {table_name} (created_at)"))
                            results['optimizations'] += 1
                            results['details'].append({
                                'type': 'Database index',
                                'table': table_name,
                                'column': 'created_at'
                            })
                            logger.info(f"Added index to {table_name}.created_at")
                        except Exception as e:
                            logger.debug(f"Could not add index to {table_name}.created_at: {str(e)}")
                        
                        # Add index to updated_at columns if they exist
                        try:
                            conn.execute(text(f"CREATE INDEX IF NOT EXISTS idx_{table_name}_updated_at ON {table_name} (updated_at)"))
                            results['optimizations'] += 1
                            results['details'].append({
                                'type': 'Database index',
                                'table': table_name,
                                'column': 'updated_at'
                            })
                            logger.info(f"Added index to {table_name}.updated_at")
                        except Exception as e:
                            logger.debug(f"Could not add index to {table_name}.updated_at: {str(e)}")
                
                # Optimize database configuration
                with self.db.engine.connect() as conn:
                    # Set work_mem for better query performance
                    conn.execute(text("SET work_mem = '8MB'"))
                    results['optimizations'] += 1
                    results['details'].append({
                        'type': 'Database config',
                        'setting': 'work_mem',
                        'value': '8MB'
                    })
                    
                    # Set maintenance_work_mem for better maintenance performance
                    conn.execute(text("SET maintenance_work_mem = '64MB'"))
                    results['optimizations'] += 1
                    results['details'].append({
                        'type': 'Database config',
                        'setting': 'maintenance_work_mem',
                        'value': '64MB'
                    })
                    
                    logger.info("Optimized PostgreSQL configuration")
            
            # Optimize SQLAlchemy
            if hasattr(self.db, 'engine'):
                # Enable connection pooling
                self.db.engine.pool_size = 10
                self.db.engine.max_overflow = 20
                results['optimizations'] += 1
                results['details'].append({
                    'type': 'SQLAlchemy config',
                    'setting': 'connection pooling',
                    'value': 'pool_size=10, max_overflow=20'
                })
                
                logger.info("Optimized SQLAlchemy connection pooling")
        
        except Exception as e:
            logger.error(f"Error tuning database: {str(e)}")
        
        # Save results to file
        self._save_optimization_results('database_tuning', results)
        
        return results
    
    def optimize_api(self) -> Dict:
        """Optimize API performance."""
        logger.info("Optimizing API performance")
        
        results = {
            'optimizations': 0,
            'details': []
        }
        
        if not self.app:
            logger.warning("Flask app not available for API optimization")
            return results
        
        try:
            # Add API response compression
            if 'COMPRESS_MIMETYPES' in self.app.config:
                if 'application/json' not in self.app.config['COMPRESS_MIMETYPES']:
                    self.app.config['COMPRESS_MIMETYPES'].append('application/json')
                    results['optimizations'] += 1
                    results['details'].append({
                        'type': 'API compression',
                        'setting': 'COMPRESS_MIMETYPES',
                        'value': 'Added application/json'
                    })
                    
                    logger.info("Enabled API response compression")
            
            # Add API response caching
            @self.app.after_request
            def add_api_cache_headers(response):
                if request.path.startswith('/api/') and request.method == 'GET':
                    # Cache GET API responses for 1 minute
                    response.headers['Cache-Control'] = 'private, max-age=60'
                    results['optimizations'] += 1
                    results['details'].append({
                        'type': 'API caching',
                        'setting': 'Cache-Control',
                        'value': 'private, max-age=60'
                    })
                
                return response
            
            logger.info("Added API response caching")
            
            # Add ETag support for API responses
            @self.app.after_request
            def add_etag_header(response):
                if request.path.startswith('/api/') and request.method == 'GET':
                    response.add_etag()
                    results['optimizations'] += 1
                    results['details'].append({
                        'type': 'API optimization',
                        'setting': 'ETag',
                        'value': 'Enabled'
                    })
                
                return response
            
            logger.info("Added ETag support for API responses")
        
        except Exception as e:
            logger.error(f"Error optimizing API: {str(e)}")
        
        # Save results to file
        self._save_optimization_results('api_optimization', results)
        
        return results
    
    def cleanup_code(self) -> Dict:
        """Clean up code and remove dead code."""
        logger.info("Cleaning up code")
        
        results = {
            'files': 0,
            'lines': 0,
            'details': []
        }
        
        try:
            # Use the CodeOptimizer to clean up code
            from app.utils.code_cleaner import CodeOptimizer
            
            optimizer = CodeOptimizer('app')
            cleanup_results = optimizer.clean_project()
            
            results['files'] = cleanup_results.get('files_cleaned', 0)
            results['lines'] = cleanup_results.get('removed_imports', 0) + cleanup_results.get('removed_dead_code', 0)
            results['details'] = cleanup_results
            
            logger.info(f"Cleaned up {results['files']} files, removed {results['lines']} lines of dead code")
        
        except Exception as e:
            logger.error(f"Error cleaning up code: {str(e)}")
        
        # Save results to file
        self._save_optimization_results('code_cleanup', results)
        
        return results
    
    def run_all_optimizations(self) -> Dict:
        """Run all optimizations."""
        logger.info("Running all optimizations")
        
        results = {
            'image_optimization': self.optimize_images(),
            'asset_minimization': self.minimize_assets(),
            'cache_optimization': self.optimize_cache(),
            'database_tuning': self.tune_database(),
            'api_optimization': self.optimize_api(),
            'code_cleanup': self.cleanup_code()
        }
        
        # Save overall results to file
        self._save_optimization_results('all_optimizations', results)
        
        return results
    
    def _save_optimization_results(self, optimization_type: str, results: Dict) -> None:
        """Save optimization results to file."""
        timestamp = time.strftime("%Y%m%d-%H%M%S")
        filename = os.path.join(self.reports_dir, f"{optimization_type}_{timestamp}.json")
        
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump({
                'timestamp': timestamp,
                'optimization_type': optimization_type,
                'results': results
            }, f, indent=2)
        
        logger.info(f"Saved {optimization_type} results to {filename}")

# Initialize final optimizer
def init_final_optimizer(app: Optional[Flask] = None, db=None) -> FinalOptimizer:
    """Initialize final optimizer."""
    optimizer = FinalOptimizer(app, db)
    logger.info("Final optimizer initialized")
    return optimizer
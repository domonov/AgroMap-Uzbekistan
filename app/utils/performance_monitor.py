"""Performance monitoring utilities for AgroMap."""
import time
import psutil
import logging
import functools
import threading
from flask import request, g, current_app
from sqlalchemy import event
from sqlalchemy.engine import Engine

# Set up logger
logger = logging.getLogger('performance')
handler = logging.FileHandler('logs/performance.log')
handler.setFormatter(logging.Formatter(
    '%(asctime)s - %(levelname)s - %(message)s'
))
logger.addHandler(handler)
logger.setLevel(logging.INFO)

class PerformanceMonitor:
    """Monitor application performance metrics."""
    
    def __init__(self, app=None):
        self.app = app
        self.metrics = {
            'response_times': [],
            'db_query_times': [],
            'memory_usage': [],
            'cpu_usage': [],
            'slow_endpoints': {},
            'slow_queries': {}
        }
        self.threshold_response_time = 500  # ms
        self.threshold_query_time = 100  # ms
        self.collection_interval = 60  # seconds
        self.resource_monitor_active = False
        
        if app is not None:
            self.init_app(app)
    
    def init_app(self, app):
        """Initialize the monitor with the Flask app."""
        self.app = app
        
        # Register before_request handler
        @app.before_request
        def before_request():
            g.start_time = time.time()
        
        # Register after_request handler
        @app.after_request
        def after_request(response):
            if hasattr(g, 'start_time'):
                # Calculate response time
                response_time = (time.time() - g.start_time) * 1000  # Convert to ms
                endpoint = request.endpoint or 'unknown'
                
                # Log slow responses
                if response_time > self.threshold_response_time:
                    logger.warning(f"Slow response: {endpoint} - {response_time:.2f}ms")
                    
                    # Track slow endpoints
                    if endpoint in self.metrics['slow_endpoints']:
                        self.metrics['slow_endpoints'][endpoint]['count'] += 1
                        self.metrics['slow_endpoints'][endpoint]['total_time'] += response_time
                    else:
                        self.metrics['slow_endpoints'][endpoint] = {
                            'count': 1,
                            'total_time': response_time
                        }
                
                # Add response time to metrics
                self.metrics['response_times'].append(response_time)
                
                # Keep only the last 1000 response times
                if len(self.metrics['response_times']) > 1000:
                    self.metrics['response_times'].pop(0)
                
                # Add Server-Timing header
                response.headers['Server-Timing'] = f'app;dur={response_time:.2f}'
                
                # Add DB timing if available
                if hasattr(g, 'db_query_time'):
                    response.headers['Server-Timing'] += f', db;dur={g.db_query_time:.2f}'
            
            return response
        
        # Set up database query monitoring
        @event.listens_for(Engine, "before_cursor_execute")
        def before_cursor_execute(conn, cursor, statement, parameters, context, executemany):
            conn.info.setdefault('query_start_time', []).append(time.time())
        
        @event.listens_for(Engine, "after_cursor_execute")
        def after_cursor_execute(conn, cursor, statement, parameters, context, executemany):
            total_time = (time.time() - conn.info['query_start_time'].pop()) * 1000  # Convert to ms
            
            # Store query time in g for access in after_request
            if not hasattr(g, 'db_query_time'):
                g.db_query_time = 0
            g.db_query_time += total_time
            
            # Log slow queries
            if total_time > self.threshold_query_time:
                query_signature = statement.split()[0:3]  # First few words as signature
                query_sig_str = ' '.join(query_signature)
                
                logger.warning(f"Slow query: {query_sig_str}... - {total_time:.2f}ms")
                
                # Track slow queries
                if query_sig_str in self.metrics['slow_queries']:
                    self.metrics['slow_queries'][query_sig_str]['count'] += 1
                    self.metrics['slow_queries'][query_sig_str]['total_time'] += total_time
                else:
                    self.metrics['slow_queries'][query_sig_str] = {
                        'count': 1,
                        'total_time': total_time
                    }
            
            # Add query time to metrics
            self.metrics['db_query_times'].append(total_time)
            
            # Keep only the last 1000 query times
            if len(self.metrics['db_query_times']) > 1000:
                self.metrics['db_query_times'].pop(0)
        
        # Start resource monitoring in a separate thread
        self.start_resource_monitoring()
    
    def start_resource_monitoring(self):
        """Start monitoring system resources in a background thread."""
        if self.resource_monitor_active:
            return
        
        self.resource_monitor_active = True
        
        def monitor_resources():
            while self.resource_monitor_active:
                try:
                    # Get CPU and memory usage
                    cpu_percent = psutil.cpu_percent(interval=1)
                    memory_percent = psutil.virtual_memory().percent
                    
                    # Add to metrics
                    self.metrics['cpu_usage'].append(cpu_percent)
                    self.metrics['memory_usage'].append(memory_percent)
                    
                    # Keep only the last 1000 measurements
                    if len(self.metrics['cpu_usage']) > 1000:
                        self.metrics['cpu_usage'].pop(0)
                    if len(self.metrics['memory_usage']) > 1000:
                        self.metrics['memory_usage'].pop(0)
                    
                    # Log high resource usage
                    if cpu_percent > 80:
                        logger.warning(f"High CPU usage: {cpu_percent}%")
                    if memory_percent > 80:
                        logger.warning(f"High memory usage: {memory_percent}%")
                    
                    # Sleep for the collection interval
                    time.sleep(self.collection_interval)
                except Exception as e:
                    logger.error(f"Error in resource monitoring: {e}")
                    time.sleep(self.collection_interval)
        
        # Start the monitoring thread
        thread = threading.Thread(target=monitor_resources, daemon=True)
        thread.start()
    
    def stop_resource_monitoring(self):
        """Stop the resource monitoring thread."""
        self.resource_monitor_active = False
    
    def get_performance_report(self):
        """Generate a performance report."""
        if not self.metrics['response_times']:
            return {
                'status': 'No data collected yet'
            }
        
        avg_response_time = sum(self.metrics['response_times']) / len(self.metrics['response_times'])
        max_response_time = max(self.metrics['response_times']) if self.metrics['response_times'] else 0
        
        avg_query_time = sum(self.metrics['db_query_times']) / len(self.metrics['db_query_times']) if self.metrics['db_query_times'] else 0
        max_query_time = max(self.metrics['db_query_times']) if self.metrics['db_query_times'] else 0
        
        avg_cpu = sum(self.metrics['cpu_usage']) / len(self.metrics['cpu_usage']) if self.metrics['cpu_usage'] else 0
        avg_memory = sum(self.metrics['memory_usage']) / len(self.metrics['memory_usage']) if self.metrics['memory_usage'] else 0
        
        # Sort slow endpoints by total time
        slow_endpoints = sorted(
            self.metrics['slow_endpoints'].items(),
            key=lambda x: x[1]['total_time'],
            reverse=True
        )[:5]  # Top 5
        
        # Sort slow queries by total time
        slow_queries = sorted(
            self.metrics['slow_queries'].items(),
            key=lambda x: x[1]['total_time'],
            reverse=True
        )[:5]  # Top 5
        
        return {
            'avg_response_time': f"{avg_response_time:.2f}ms",
            'max_response_time': f"{max_response_time:.2f}ms",
            'avg_query_time': f"{avg_query_time:.2f}ms",
            'max_query_time': f"{max_query_time:.2f}ms",
            'avg_cpu_usage': f"{avg_cpu:.2f}%",
            'avg_memory_usage': f"{avg_memory:.2f}%",
            'slow_endpoints': [{
                'endpoint': endpoint,
                'count': data['count'],
                'avg_time': f"{data['total_time'] / data['count']:.2f}ms"
            } for endpoint, data in slow_endpoints],
            'slow_queries': [{
                'query': query,
                'count': data['count'],
                'avg_time': f"{data['total_time'] / data['count']:.2f}ms"
            } for query, data in slow_queries]
        }

# Decorator for monitoring function execution time
def monitor_execution_time(func=None, threshold=100, name=None):
    """Decorator to monitor function execution time."""
    if func is None:
        return functools.partial(
            monitor_execution_time, 
            threshold=threshold,
            name=name
        )
    
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        start_time = time.time()
        result = func(*args, **kwargs)
        execution_time = (time.time() - start_time) * 1000  # Convert to ms
        
        func_name = name or func.__name__
        
        if execution_time > threshold:
            logger.warning(f"Slow function: {func_name} - {execution_time:.2f}ms")
        
        return result
    
    return wrapper
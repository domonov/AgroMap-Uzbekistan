"""Monitoring system utilities for AgroMap."""
import os
import json
import time
import logging
import psutil
import threading
import datetime
import sqlite3
from typing import Dict, List, Optional, Any, Union, Tuple
from flask import Flask, request, g, current_app
from prometheus_client import start_http_server, Counter, Histogram, Gauge, CollectorRegistry

# Set up logger
logger = logging.getLogger('monitoring')
handler = logging.FileHandler('logs/monitoring.log')
handler.setFormatter(logging.Formatter(
    '%(asctime)s - %(levelname)s - %(message)s'
))
logger.addHandler(handler)
logger.setLevel(logging.INFO)

class MonitoringSystem:
    """System monitoring for AgroMap."""
    
    def __init__(self, app: Optional[Flask] = None, db=None):
        self.app = app
        self.db = db
        self.monitoring_active = False
        self.monitoring_thread = None
        self.collection_interval = 60  # seconds
        self.retention_period = 30  # days
        self.metrics_db = 'data/monitoring/metrics.db'
        self.charts_dir = 'data/monitoring/charts'
        self.reports_dir = 'data/monitoring/reports'
        
        # Create directories if they don't exist
        os.makedirs(os.path.dirname(self.metrics_db), exist_ok=True)
        os.makedirs(self.charts_dir, exist_ok=True)
        os.makedirs(self.reports_dir, exist_ok=True)
        os.makedirs('logs', exist_ok=True)
        
        # Create registry
        self.registry = CollectorRegistry()
        
        # Initialize metrics
        self.metrics = {
            'requests': Counter('http_requests_total', 
                              'Total HTTP requests',
                              ['method', 'endpoint'],
                              registry=self.registry),
            'response_time': Histogram('http_response_time_seconds',
                                     'HTTP response time',
                                     registry=self.registry),
            'memory_usage': Gauge('memory_usage_bytes',
                                'Memory usage in bytes',
                                registry=self.registry),
            'cpu_usage': Gauge('cpu_usage_percent',
                             'CPU usage percentage',
                             registry=self.registry),
            'active_users': Gauge('active_users',
                                'Number of active users',
                                registry=self.registry),
            'api_calls': Counter('api_calls_total',
                               'Total API calls',
                               ['endpoint'],
                               registry=self.registry),
            'errors': Counter('errors_total',
                            'Total errors',
                            ['type'],
                            registry=self.registry)
        }
        
        # Initialize metrics database
        self._init_metrics_db()
        
        if app is not None:
            self.init_app(app, db)
    
    def init_app(self, app: Flask, db=None):
        """Initialize with Flask app."""
        self.app = app
        self.db = db
        
        # Start metrics server if not testing
        if not app.config.get('TESTING'):
            metrics_port = app.config.get('METRICS_PORT', 9090)
            start_http_server(metrics_port, registry=self.registry)
        
        # Request monitoring
        @app.before_request
        def before_request():
            request.start_time = time.time()

        @app.after_request
        def after_request(response):
            # Record request metrics
            endpoint = request.endpoint or 'unknown'
            self.metrics['requests'].labels(
                method=request.method,
                endpoint=endpoint
            ).inc()

            # Record response time
            if hasattr(request, 'start_time'):
                response_time = time.time() - request.start_time
                self.metrics['response_time'].observe(response_time)

            # Track API calls
            if request.path.startswith('/api/'):
                self.metrics['api_calls'].labels(
                    endpoint=request.path
                ).inc()

            # Track errors
            if 400 <= response.status_code < 600:
                self.metrics['errors'].labels(
                    type=str(response.status_code)
                ).inc()

            return response
        
        # Register commands
        @app.cli.command("start-monitoring")
        def start_monitoring_command():
            """Start system monitoring."""
            self.start_monitoring()
            print("System monitoring started.")
        
        @app.cli.command("stop-monitoring")
        def stop_monitoring_command():
            """Stop system monitoring."""
            self.stop_monitoring()
            print("System monitoring stopped.")
        
        @app.cli.command("generate-monitoring-report")
        def generate_report_command():
            """Generate monitoring report."""
            report_file = self.generate_report()
            print(f"Monitoring report generated: {report_file}")
        
        # Start monitoring thread
        self.start_monitoring()
    
    def _init_metrics_db(self):
        """Initialize metrics database."""
        try:
            conn = sqlite3.connect(self.metrics_db)
            cursor = conn.cursor()
            
            # Create system metrics table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS system_metrics (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp TEXT NOT NULL,
                    cpu_usage REAL,
                    memory_usage REAL,
                    disk_usage REAL,
                    network_sent REAL,
                    network_received REAL,
                    process_count INTEGER
                )
            ''')
            
            # Create request metrics table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS request_metrics (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp TEXT NOT NULL,
                    endpoint TEXT,
                    method TEXT,
                    status_code INTEGER,
                    response_time REAL,
                    db_time REAL
                )
            ''')
            
            # Create error metrics table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS error_metrics (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp TEXT NOT NULL,
                    error_type TEXT,
                    error_message TEXT,
                    endpoint TEXT,
                    method TEXT
                )
            ''')
            
            # Create user activity table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS user_activity (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp TEXT NOT NULL,
                    user_id TEXT,
                    action TEXT,
                    resource TEXT
                )
            ''')
            
            # Create API usage table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS api_usage (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp TEXT NOT NULL,
                    endpoint TEXT,
                    method TEXT,
                    user_id TEXT,
                    response_time REAL,
                    status_code INTEGER
                )
            ''')
            
            # Create database metrics table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS db_metrics (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp TEXT NOT NULL,
                    query_type TEXT,
                    table_name TEXT,
                    execution_time REAL,
                    row_count INTEGER
                )
            ''')
            
            # Create security events table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS security_events (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp TEXT NOT NULL,
                    event_type TEXT,
                    user_id TEXT,
                    ip_address TEXT,
                    details TEXT
                )
            ''')
            
            # Create metrics table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS metrics (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp TEXT NOT NULL,
                    metric_name TEXT NOT NULL,
                    value REAL,
                    labels TEXT
                )
            ''')
            
            conn.commit()
            conn.close()
            
            logger.info("Metrics database initialized")
        
        except Exception as e:
            logger.error(f"Error initializing metrics database: {str(e)}")
    
    def _collect_system_metrics(self):
        """Collect system metrics."""
        try:
            # Get memory info
            memory = psutil.virtual_memory()
            self.metrics['memory_usage'].set(memory.used)
            
            # Get CPU usage (as a percentage)
            cpu_percent = psutil.cpu_percent(interval=1)
            self.metrics['cpu_usage'].set(cpu_percent)
            
            # Write to database
            self._write_metric('memory_usage', memory.used)
            self._write_metric('cpu_usage', cpu_percent)
        
        except Exception as e:
            logger.error(f'Error collecting system metrics: {e}')

    def start_monitoring(self):
        """Start the monitoring system."""
        if not self.monitoring_active:
            self.monitoring_active = True
            self._collect_system_metrics()  # Collect initial metrics
            
            def monitor():
                while self.monitoring_active:
                    try:
                        self._collect_system_metrics()
                        time.sleep(self.collection_interval)
                    except Exception as e:
                        logger.error(f'Error in monitoring thread: {e}')
                        time.sleep(1)  # Avoid spinning if there's an error
            
            self.monitoring_thread = threading.Thread(target=monitor, daemon=True)
            self.monitoring_thread.start()
            logger.info('System monitoring thread started')
    
    def stop_monitoring(self):
        """Stop the monitoring thread."""
        self.monitoring_active = False
        if self.monitoring_thread:
            self.monitoring_thread.join(timeout=1.0)
            logger.info("System monitoring thread stopped")
    
    def stop(self):
        """Stop the monitoring system."""
        if self.monitoring_active:
            self.monitoring_active = False
            if self.monitoring_thread:
                self.monitoring_thread.join()
            logger.info("Monitoring system stopped")
    
    def collect_system_metrics(self):
        """Collect system metrics."""
        try:
            # Get CPU usage
            cpu_usage = psutil.cpu_percent(interval=1)
            
            # Get memory usage
            memory = psutil.virtual_memory()
            memory_usage = memory.percent
            
            # Get disk usage
            disk = psutil.disk_usage('/')
            disk_usage = disk.percent
            
            # Get network I/O
            net_io = psutil.net_io_counters()
            network_sent = net_io.bytes_sent
            network_received = net_io.bytes_recv
            
            # Get process count
            process_count = len(psutil.pids())
            
            # Log to database
            conn = sqlite3.connect(self.metrics_db)
            cursor = conn.cursor()
            
            cursor.execute('''
                INSERT INTO system_metrics (
                    timestamp, cpu_usage, memory_usage, disk_usage,
                    network_sent, network_received, process_count
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', (
                datetime.datetime.now().isoformat(),
                cpu_usage,
                memory_usage,
                disk_usage,
                network_sent,
                network_received,
                process_count
            ))
            
            conn.commit()
            conn.close()
            
            # Log high resource usage
            if cpu_usage > 80:
                logger.warning(f"High CPU usage: {cpu_usage}%")
            if memory_usage > 80:
                logger.warning(f"High memory usage: {memory_usage}%")
            if disk_usage > 80:
                logger.warning(f"High disk usage: {disk_usage}%")
            
            return {
                'cpu_usage': cpu_usage,
                'memory_usage': memory_usage,
                'disk_usage': disk_usage,
                'network_sent': network_sent,
                'network_received': network_received,
                'process_count': process_count
            }
        
        except Exception as e:
            logger.error(f"Error collecting system metrics: {str(e)}")
            return None
    
    def log_request_metric(self, endpoint: str, method: str, status_code: int,
                         response_time: float, db_time: float = 0):
        """Log a request metric."""
        try:
            conn = sqlite3.connect(self.metrics_db)
            cursor = conn.cursor()
            
            cursor.execute('''
                INSERT INTO request_metrics (
                    timestamp, endpoint, method, status_code, response_time, db_time
                ) VALUES (?, ?, ?, ?, ?, ?)
            ''', (
                datetime.datetime.now().isoformat(),
                endpoint,
                method,
                status_code,
                response_time,
                db_time
            ))
            
            conn.commit()
            conn.close()
            
            # Log slow requests
            if response_time > 1000:  # More than 1 second
                logger.warning(f"Slow request: {method} {endpoint} - {response_time:.2f}ms")
            
            # Log API usage if it's an API endpoint
            if endpoint.startswith('api.'):
                self.log_api_usage(
                    endpoint=endpoint,
                    method=method,
                    user_id=getattr(g, 'user_id', None),
                    response_time=response_time,
                    status_code=status_code
                )
            
            return True
        
        except Exception as e:
            logger.error(f"Error logging request metric: {str(e)}")
            return False
    
    def log_error_metric(self, error_type: str, error_message: str,
                       endpoint: str, method: str):
        """Log an error metric."""
        try:
            conn = sqlite3.connect(self.metrics_db)
            cursor = conn.cursor()
            
            cursor.execute('''
                INSERT INTO error_metrics (
                    timestamp, error_type, error_message, endpoint, method
                ) VALUES (?, ?, ?, ?, ?)
            ''', (
                datetime.datetime.now().isoformat(),
                error_type,
                error_message,
                endpoint,
                method
            ))
            
            conn.commit()
            conn.close()
            
            logger.error(f"Error in {method} {endpoint}: {error_type} - {error_message}")
            
            return True
        
        except Exception as e:
            logger.error(f"Error logging error metric: {str(e)}")
            return False
    
    def log_user_activity(self, user_id: str, action: str, resource: str):
        """Log user activity."""
        try:
            conn = sqlite3.connect(self.metrics_db)
            cursor = conn.cursor()
            
            cursor.execute('''
                INSERT INTO user_activity (
                    timestamp, user_id, action, resource
                ) VALUES (?, ?, ?, ?)
            ''', (
                datetime.datetime.now().isoformat(),
                user_id,
                action,
                resource
            ))
            
            conn.commit()
            conn.close()
            
            logger.info(f"User activity: {user_id} {action} {resource}")
            
            return True
        
        except Exception as e:
            logger.error(f"Error logging user activity: {str(e)}")
            return False
    
    def log_api_usage(self, endpoint: str, method: str, user_id: Optional[str],
                    response_time: float, status_code: int):
        """Log API usage."""
        try:
            conn = sqlite3.connect(self.metrics_db)
            cursor = conn.cursor()
            
            cursor.execute('''
                INSERT INTO api_usage (
                    timestamp, endpoint, method, user_id, response_time, status_code
                ) VALUES (?, ?, ?, ?, ?, ?)
            ''', (
                datetime.datetime.now().isoformat(),
                endpoint,
                method,
                user_id,
                response_time,
                status_code
            ))
            
            conn.commit()
            conn.close()
            
            return True
        
        except Exception as e:
            logger.error(f"Error logging API usage: {str(e)}")
            return False
    
    def log_db_metric(self, query_type: str, table_name: str,
                    execution_time: float, row_count: int = 0):
        """Log database metric."""
        try:
            conn = sqlite3.connect(self.metrics_db)
            cursor = conn.cursor()
            
            cursor.execute('''
                INSERT INTO db_metrics (
                    timestamp, query_type, table_name, execution_time, row_count
                ) VALUES (?, ?, ?, ?, ?)
            ''', (
                datetime.datetime.now().isoformat(),
                query_type,
                table_name,
                execution_time,
                row_count
            ))
            
            conn.commit()
            conn.close()
            
            # Log slow queries
            if execution_time > 500:  # More than 500ms
                logger.warning(f"Slow query: {query_type} on {table_name} - {execution_time:.2f}ms")
            
            return True
        
        except Exception as e:
            logger.error(f"Error logging DB metric: {str(e)}")
            return False
    
    def log_security_event(self, event_type: str, user_id: Optional[str],
                         ip_address: str, details: str):
        """Log security event."""
        try:
            conn = sqlite3.connect(self.metrics_db)
            cursor = conn.cursor()
            
            cursor.execute('''
                INSERT INTO security_events (
                    timestamp, event_type, user_id, ip_address, details
                ) VALUES (?, ?, ?, ?, ?)
            ''', (
                datetime.datetime.now().isoformat(),
                event_type,
                user_id,
                ip_address,
                details
            ))
            
            conn.commit()
            conn.close()
            
            logger.warning(f"Security event: {event_type} by {user_id or 'anonymous'} from {ip_address} - {details}")
            
            return True
        
        except Exception as e:
            logger.error(f"Error logging security event: {str(e)}")
            return False
    
    def cleanup_old_metrics(self):
        """Clean up old metrics."""
        try:
            # Calculate cutoff date
            cutoff_date = (datetime.datetime.now() - datetime.timedelta(days=self.retention_period)).isoformat()
            
            conn = sqlite3.connect(self.metrics_db)
            cursor = conn.cursor()
            
            # Delete old metrics from each table
            tables = [
                'system_metrics',
                'request_metrics',
                'error_metrics',
                'user_activity',
                'api_usage',
                'db_metrics',
                'security_events'
            ]
            
            for table in tables:
                cursor.execute(f"DELETE FROM {table} WHERE timestamp < ?", (cutoff_date,))
            
            conn.commit()
            conn.close()
            
            logger.info(f"Cleaned up metrics older than {cutoff_date}")
            
            return True
        
        except Exception as e:
            logger.error(f"Error cleaning up old metrics: {str(e)}")
            return False
    
    def generate_report(self):
        """Generate a monitoring report."""
        try:
            # Create report filename with timestamp
            timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
            report_file = os.path.join(self.reports_dir, f"monitoring_report_{timestamp}.json")
            
            # Get system health for different time periods
            health_24h = self.get_system_health(period=24)
            health_7d = self.get_system_health(period=24*7)
            
            # Create report data
            report_data = {
                'generated_at': datetime.datetime.now().isoformat(),
                'system_health': {
                    'last_24h': health_24h,
                    'last_7d': health_7d
                },
                'current_metrics': self.collect_system_metrics()
            }
            
            # Write report to file
            with open(report_file, 'w', encoding='utf-8') as f:
                json.dump(report_data, f, indent=2)
            
            logger.info(f"Generated monitoring report: {report_file}")
            
            return report_file
        
        except Exception as e:
            logger.error(f"Error generating monitoring report: {str(e)}")
            return None
    
    def get_system_health(self, period: int = 24) -> Dict:
        """Get system health metrics for the specified period (hours)."""
        try:
            # Calculate start time
            start_time = (datetime.datetime.now() - datetime.timedelta(hours=period)).isoformat()
            
            conn = sqlite3.connect(self.metrics_db)
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            
            # Get system metrics
            cursor.execute('''
                SELECT 
                    AVG(cpu_usage) as avg_cpu,
                    MAX(cpu_usage) as max_cpu,
                    AVG(memory_usage) as avg_memory,
                    MAX(memory_usage) as max_memory,
                    AVG(disk_usage) as avg_disk,
                    MAX(disk_usage) as max_disk,
                    AVG(process_count) as avg_processes
                FROM system_metrics
                WHERE timestamp >= ?
            ''', (start_time,))
            
            system_metrics = dict(cursor.fetchone() or {})
            
            # Get request metrics
            cursor.execute('''
                SELECT 
                    COUNT(*) as total_requests,
                    AVG(response_time) as avg_response_time,
                    MAX(response_time) as max_response_time,
                    SUM(CASE WHEN status_code >= 500 THEN 1 ELSE 0 END) as server_errors,
                    SUM(CASE WHEN status_code >= 400 AND status_code < 500 THEN 1 ELSE 0 END) as client_errors,
                    SUM(CASE WHEN status_code < 400 THEN 1 ELSE 0 END) as successful_requests
                FROM request_metrics
                WHERE timestamp >= ?
            ''', (start_time,))
            
            request_metrics = dict(cursor.fetchone() or {})
            
            # Get error metrics
            cursor.execute('''
                SELECT COUNT(*) as total_errors
                FROM error_metrics
                WHERE timestamp >= ?
            ''', (start_time,))
            
            error_metrics = dict(cursor.fetchone() or {})
            
            conn.close()
            
            # Create health status
            health_status = "healthy"
            
            # Handle empty results
            if not system_metrics or 'avg_cpu' not in system_metrics:
                return {
                    'status': 'unknown',
                    'message': 'No system metrics available for this period'
                }
            
            # Calculate error rate
            total_requests = request_metrics.get('total_requests', 0)
            total_errors = error_metrics.get('total_errors', 0)
            
            if total_requests > 0:
                error_rate = (total_errors / total_requests) * 100
            else:
                error_rate = 0
            
            # Determine health status
            if system_metrics.get('max_cpu', 0) > 80 or system_metrics.get('max_memory', 0) > 80 or error_rate > 5:
                health_status = "warning"
            if system_metrics.get('max_cpu', 0) > 90 or system_metrics.get('max_memory', 0) > 90 or error_rate > 10:
                health_status = "critical"
            
            return {
                'status': health_status,
                'period_hours': period,
                'system': {
                    'cpu': {
                        'avg': round(system_metrics.get('avg_cpu', 0), 2),
                        'max': round(system_metrics.get('max_cpu', 0), 2)
                    },
                    'memory': {
                        'avg': round(system_metrics.get('avg_memory', 0), 2),
                        'max': round(system_metrics.get('max_memory', 0), 2)
                    },
                    'disk': {
                        'avg': round(system_metrics.get('avg_disk', 0), 2),
                        'max': round(system_metrics.get('max_disk', 0), 2)
                    },
                    'processes': round(system_metrics.get('avg_processes', 0), 2)
                },
                'requests': {
                    'total': request_metrics.get('total_requests', 0),
                    'successful': request_metrics.get('successful_requests', 0),
                    'client_errors': request_metrics.get('client_errors', 0),
                    'server_errors': request_metrics.get('server_errors', 0),
                    'avg_response_time': round(request_metrics.get('avg_response_time', 0) or 0, 2),
                    'max_response_time': round(request_metrics.get('max_response_time', 0) or 0, 2)
                },
                'errors': {
                    'total': error_metrics.get('total_errors', 0),
                    'rate': round(error_rate, 2)
                }
            }
        
        except Exception as e:
            logger.error(f"Error getting system health: {str(e)}")
            return {
                'status': 'unknown',
                'error': str(e)
            }
    
    def _write_metric(self, metric_name: str, value: float, labels: dict = None):
        """Write a metric value to the database."""
        try:
            with sqlite3.connect(self.metrics_db) as conn:
                cursor = conn.cursor()
                timestamp = datetime.datetime.utcnow().isoformat()
                cursor.execute(
                    'INSERT INTO metrics (timestamp, metric_name, value, labels) VALUES (?, ?, ?, ?)',
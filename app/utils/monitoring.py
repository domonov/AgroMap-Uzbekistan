"""Application monitoring configuration for AgroMap."""
import os
import psutil
import logging
from typing import Dict, Any
from flask import Flask, request
import time
from datadog import initialize, statsd
from prometheus_client import start_http_server, Counter, Histogram, Gauge
import threading

# Set up logging
logger = logging.getLogger(__name__)

class MonitoringSystem:
    """System for monitoring application metrics."""

    def __init__(self, app: Flask = None):
        self.app = app
        self.metrics = {
            'requests': Counter('http_requests_total', 'Total HTTP requests', ['method', 'endpoint']),
            'response_time': Histogram('http_response_time_seconds', 'HTTP response time'),
            'memory_usage': Gauge('memory_usage_bytes', 'Memory usage in bytes'),
            'cpu_usage': Gauge('cpu_usage_percent', 'CPU usage percentage'),
            'active_users': Gauge('active_users', 'Number of active users'),
            'api_calls': Counter('api_calls_total', 'Total API calls', ['endpoint']),
            'errors': Counter('errors_total', 'Total errors', ['type'])
        }

        # Initialize monitoring systems
        if app is not None:
            self.init_app(app)

    def init_app(self, app: Flask):
        """Initialize with Flask application."""
        self.app = app

        # Start Prometheus metrics server
        start_http_server(app.config.get('METRICS_PORT', 9090))

        # Initialize DataDog if configured
        if app.config.get('DATADOG_API_KEY'):
            initialize(
                api_key=app.config.get('DATADOG_API_KEY'),
                app_key=app.config.get('DATADOG_APP_KEY')
            )

        # Start system metrics collection
        self._start_system_metrics_collection()

        # Request monitoring
        @app.before_request
        def before_request():
            request.start_time = time.time()

        @app.after_request
        def after_request(response):
            # Record request metrics
            self.metrics['requests'].labels(
                method=request.method,
                endpoint=request.endpoint or 'unknown'
            ).inc()

            # Record response time
            if hasattr(request, 'start_time'):
                response_time = time.time() - request.start_time
                self.metrics['response_time'].observe(response_time)

                # Send to DataDog if configured
                if app.config.get('DATADOG_API_KEY'):
                    statsd.histogram(
                        'agromap.response_time',
                        response_time,
                        tags=[f"endpoint:{request.endpoint or 'unknown'}"]
                    )

            # Track API calls
            if request.path.startswith('/api/'):
                self.metrics['api_calls'].labels(endpoint=request.path).inc()

            # Track errors
            if 400 <= response.status_code < 600:
                self.metrics['errors'].labels(
                    type=str(response.status_code)
                ).inc()

            return response

        # Error monitoring
        @app.errorhandler(Exception)
        def handle_error(error):
            self.metrics['errors'].labels(
                type=error.__class__.__name__
            ).inc()
            raise error

    def _collect_system_metrics(self):
        """Collect system metrics periodically."""
        while True:
            try:
                # Memory usage
                memory = psutil.Process(os.getpid()).memory_info()
                self.metrics['memory_usage'].set(memory.rss)

                # CPU usage
                cpu = psutil.Process(os.getpid()).cpu_percent()
                self.metrics['cpu_usage'].set(cpu)

                # Send to DataDog if configured
                if self.app.config.get('DATADOG_API_KEY'):
                    statsd.gauge('agromap.memory_usage', memory.rss)
                    statsd.gauge('agromap.cpu_usage', cpu)

            except Exception as e:
                logger.error(f"Error collecting system metrics: {e}")

            time.sleep(60)  # Collect every minute

    def _start_system_metrics_collection(self):
        """Start system metrics collection in background thread."""
        thread = threading.Thread(
            target=self._collect_system_metrics,
            daemon=True
        )
        thread.start()

    def record_user_activity(self, user_id: str):
        """Record user activity."""
        self.metrics['active_users'].inc()

    def record_user_logout(self, user_id: str):
        """Record user logout."""
        self.metrics['active_users'].dec()

    def get_current_metrics(self) -> Dict[str, Any]:
        """Get current metrics values."""
        return {
            'memory_usage': psutil.Process(os.getpid()).memory_info().rss,
            'cpu_usage': psutil.Process(os.getpid()).cpu_percent(),
            'active_users': self.metrics['active_users']._value.get(),
            'requests_total': sum(self.metrics['requests']._metrics.values()),
            'errors_total': sum(self.metrics['errors']._metrics.values())
        }

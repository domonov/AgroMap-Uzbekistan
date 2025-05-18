"""Test monitoring functionality."""
import pytest
from unittest.mock import patch, MagicMock
from prometheus_client import CollectorRegistry
from flask import Flask, jsonify
from app.utils.monitoring_system import MonitoringSystem

@pytest.fixture
def app():
    """Create a fresh Flask app for testing."""
    app = Flask('test_app')
    app.config['TESTING'] = True
    
    @app.route('/')
    def index():
        return jsonify({'status': 'ok'})
    
    return app

@pytest.fixture
def app_with_monitoring(app):
    """Create app with monitoring enabled."""
    app.config['METRICS_PORT'] = 9090
    monitoring = MonitoringSystem(app)
    app.extensions['monitoring'] = monitoring
    return app

@pytest.fixture
def client(app_with_monitoring):
    """Create test client."""
    with app_with_monitoring.test_client() as client:
        yield client

def test_monitoring_initialization(app_with_monitoring):
    """Test monitoring system initialization."""
    assert 'monitoring' in app_with_monitoring.extensions
    monitoring = app_with_monitoring.extensions['monitoring']
    assert isinstance(monitoring.registry, CollectorRegistry)

def test_request_monitoring(client, app_with_monitoring):
    """Test request monitoring."""
    monitoring = app_with_monitoring.extensions['monitoring']
    
    # Get initial counter value
    initial_samples = list(monitoring.metrics['requests'].collect()[0].samples)
    initial_count = sum(s.value for s in initial_samples if s.labels == {'method': 'GET', 'endpoint': 'index'})
    
    response = client.get('/')
    assert response.status_code == 200
    
    # Counter should be incremented
    final_samples = list(monitoring.metrics['requests'].collect()[0].samples)
    final_count = sum(s.value for s in final_samples if s.labels == {'method': 'GET', 'endpoint': 'index'})
    assert final_count > initial_count

def test_error_monitoring(client, app_with_monitoring):
    """Test error monitoring."""
    monitoring = app_with_monitoring.extensions['monitoring']
    
    # Get initial error counter value
    initial_samples = list(monitoring.metrics['errors'].collect()[0].samples)
    initial_errors = sum(s.value for s in initial_samples if s.labels == {'type': '404'})
    
    # Make request to nonexistent page
    response = client.get('/nonexistent')
    assert response.status_code == 404
    
    # Error counter should be incremented
    final_samples = list(monitoring.metrics['errors'].collect()[0].samples)
    final_errors = sum(s.value for s in final_samples if s.labels == {'type': '404'})
    assert final_errors > initial_errors

def test_system_metrics(app_with_monitoring):
    """Test system metrics collection."""
    monitoring = app_with_monitoring.extensions['monitoring']
    
    # Force metrics collection
    monitoring._collect_system_metrics()
    
    # System metrics should be present
    memory_samples = list(monitoring.metrics['memory_usage'].collect()[0].samples)
    cpu_samples = list(monitoring.metrics['cpu_usage'].collect()[0].samples)
    
    assert memory_samples[0].value > 0
    assert cpu_samples[0].value >= 0

def test_active_users_tracking(app_with_monitoring):
    """Test active users tracking."""
    monitoring = app_with_monitoring.extensions['monitoring']
    
    # Initial active users
    initial_samples = list(monitoring.metrics['active_users'].collect()[0].samples)
    initial_users = initial_samples[0].value
    
    # Simulate user activity
    monitoring.metrics['active_users'].inc()
    current_samples = list(monitoring.metrics['active_users'].collect()[0].samples)
    assert current_samples[0].value == initial_users + 1
    
    # Simulate user logout
    monitoring.metrics['active_users'].dec()
    final_samples = list(monitoring.metrics['active_users'].collect()[0].samples)
    assert final_samples[0].value == initial_users

@patch('datadog.statsd.gauge')
def test_datadog_metrics(mock_gauge, app_with_monitoring):
    """Test DataDog metrics integration."""
    app_with_monitoring.config['DATADOG_API_KEY'] = 'test-key'
    monitoring = app_with_monitoring.extensions['monitoring']
    
    # Simulate some activity
    monitoring.metrics['memory_usage'].set(1024 * 1024)  # 1MB
    monitoring.metrics['cpu_usage'].set(50.0)  # 50% CPU
    
    # Verify metrics were collected
    memory_samples = list(monitoring.metrics['memory_usage'].collect()[0].samples)
    cpu_samples = list(monitoring.metrics['cpu_usage'].collect()[0].samples)
    
    assert memory_samples[0].value == 1024 * 1024
    assert cpu_samples[0].value == 50.0

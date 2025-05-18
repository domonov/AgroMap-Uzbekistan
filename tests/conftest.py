"""Test configuration and fixtures."""
import os
import pytest
import tempfile
from flask import Flask
from flask.testing import FlaskClient
from app import db as _db
from app.models import User
from app.utils.monitoring_system import MonitoringSystem

def create_test_app():
    """Create a Flask app for testing."""
    app = Flask(__name__)
    app.config.update({
        'TESTING': True,
        'SQLALCHEMY_DATABASE_URI': 'sqlite:///:memory:',
        'WTF_CSRF_ENABLED': False,
        'SERVER_NAME': 'localhost.localdomain',
        'SECRET_KEY': 'test-key',
        'METRICS_PORT': 9090,
        'MONITORING_ENABLED': True,
        'MONITORING_INTERVAL': 5,  # 5 seconds for testing
    })
    return app

@pytest.fixture(scope='session')
def app():
    """App fixture for tests."""
    _app = create_test_app()
    
    # Create temp folder for test files
    with tempfile.TemporaryDirectory() as temp_dir:
        _app.config['UPLOAD_FOLDER'] = temp_dir
        _app.config['MONITORING_DATA_DIR'] = os.path.join(temp_dir, 'monitoring')
        
        with _app.app_context():
            _db.init_app(_app)
            _db.create_all()
            
            # Initialize monitoring system
            monitoring = MonitoringSystem(_app, _db)
            _app.extensions['monitoring'] = monitoring
            
            yield _app
            
            # Clean up monitoring
            monitoring.stop()
            _db.session.remove()
            _db.drop_all()

@pytest.fixture
def client(app):
    """Test client fixture."""
    return app.test_client()

@pytest.fixture
def runner(app):
    """Test CLI runner fixture."""
    return app.test_cli_runner()

@pytest.fixture(scope='function')
def db(app):
    """Database fixture for tests."""
    with app.app_context():
        _db.create_all()
        yield _db
        _db.session.remove()
        _db.drop_all()

@pytest.fixture
def test_user(db):
    """Create a test user."""
    user = User(
        username='testuser',
        email='test@example.com',
        password_hash='pbkdf2:sha256:abc123'
    )
    db.session.add(user)
    db.session.commit()
    return user

class AuthActions:
    """Authentication actions for tests."""
    def __init__(self, client: FlaskClient):
        self._client = client

    def login(self, email='test@example.com', password='testpass'):
        """Log in as test user."""
        return self._client.post('/auth/login', data={
            'email': email,
            'password': password
        })

    def logout(self):
        """Log out the current user."""
        return self._client.get('/auth/logout')

@pytest.fixture
def auth(client):
    """Authentication fixture."""
    return AuthActions(client)

@pytest.fixture
def monitoring(app):
    """Monitoring system fixture."""
    return app.extensions['monitoring']

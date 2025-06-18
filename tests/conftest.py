"""
Enterprise Testing Configuration and Fixtures

Comprehensive testing setup with fixtures for database, authentication,
mocking external services, and performance testing utilities.

Author: FlytBase Assignment - Enterprise Edition
Created: 2024
"""

import pytest
import tempfile
import os
from unittest.mock import Mock, patch
from datetime import datetime, timedelta
from typing import Generator, Dict, Any, Optional

from flask import Flask
from flask.testing import FlaskClient

# Import application components
from backend.app import create_app
from backend.app.core.config_manager import get_config
from backend.app.core.base_service import ServiceRegistry


@pytest.fixture(scope="session")
def app() -> Generator[Flask, None, None]:
    """Create application instance for testing."""
    # Set testing environment
    os.environ['FLASK_ENV'] = 'testing'
    
    # Create temporary database
    db_fd, db_path = tempfile.mkstemp(suffix='.db')
    os.environ['DATABASE_URL'] = f'sqlite:///{db_path}'
    
    try:
        # Create app
        app = create_app('testing')
        
        # Establish application context
        with app.app_context():
            # Initialize database tables
            from backend.app.models import db
            db.create_all()
            
            yield app
            
            # Cleanup
            db.drop_all()
    
    finally:
        os.close(db_fd)
        os.unlink(db_path)


@pytest.fixture(scope="function")
def client(app: Flask) -> FlaskClient:
    """Create test client."""
    return app.test_client()


@pytest.fixture(scope="function")
def db_session(app: Flask):
    """Create database session for testing."""
    from backend.app.models import db
    
    with app.app_context():
        # Begin transaction
        connection = db.engine.connect()
        transaction = connection.begin()
        
        # Configure session
        db.session.configure(bind=connection)
        
        yield db.session
        
        # Rollback transaction
        transaction.rollback()
        connection.close()
        db.session.remove()


@pytest.fixture
def auth_headers() -> Dict[str, str]:
    """Create authentication headers for testing."""
    # Mock JWT token
    token = "mock.jwt.token"
    return {
        'Authorization': f'Bearer {token}',
        'Content-Type': 'application/json'
    }


@pytest.fixture
def sample_drone_data() -> Dict[str, Any]:
    """Sample drone data for testing."""
    return {
        "id": "drone-001",
        "name": "Survey Drone Alpha",
        "status": "available",
        "battery_percentage": 85.5,
        "location": {
            "latitude": 37.7749,
            "longitude": -122.4194,
            "altitude": 0.0
        },
        "specifications": {
            "max_flight_time": 25,
            "max_altitude": 400,
            "camera_resolution": "4K",
            "payload_capacity": 1.5
        }
    }


@pytest.fixture
def sample_mission_data() -> Dict[str, Any]:
    """Sample mission data for testing."""
    return {
        "id": "mission-001",
        "name": "Agricultural Survey",
        "status": "planned",
        "survey_area": {
            "type": "Polygon",
            "coordinates": [[
                [-122.4194, 37.7749],
                [-122.4094, 37.7749],
                [-122.4094, 37.7649],
                [-122.4194, 37.7649],
                [-122.4194, 37.7749]
            ]]
        },
        "altitude_m": 100.0,
        "overlap_percentage": 60.0,
        "estimated_duration": 45,
        "waypoints": []
    }


@pytest.fixture
def mock_weather_service():
    """Mock weather service for testing."""
    with patch('backend.app.services.weather_service.WeatherService') as mock:
        # Configure mock responses
        mock.return_value.get_weather_data.return_value = {
            "temperature": 22.5,
            "humidity": 65,
            "wind_speed": 8.2,
            "wind_direction": 180,
            "visibility": 10000,
            "conditions": "clear",
            "flight_suitability": "excellent"
        }
        
        mock.return_value.get_weather_forecast.return_value = [
            {
                "timestamp": datetime.utcnow() + timedelta(hours=i),
                "temperature": 20 + i,
                "wind_speed": 5 + i,
                "conditions": "clear"
            }
            for i in range(24)
        ]
        
        yield mock


@pytest.fixture
def mock_ai_service():
    """Mock AI service for testing."""
    with patch('backend.app.services.ai_service.AIService') as mock:
        # Configure mock AI responses
        mock.return_value.optimize_mission.return_value = {
            "optimized_waypoints": [
                {"latitude": 37.7749, "longitude": -122.4194, "altitude": 100},
                {"latitude": 37.7750, "longitude": -122.4193, "altitude": 100}
            ],
            "estimated_flight_time": 35,
            "confidence": 0.92,
            "efficiency_improvement": 15.3
        }
        
        mock.return_value.predict_success.return_value = {
            "success_probability": 0.89,
            "risk_factors": ["high_wind_forecast"],
            "recommendations": ["postpone_if_wind_exceeds_15kph"],
            "confidence": 0.94
        }
        
        yield mock


@pytest.fixture
def mock_external_services(mock_weather_service, mock_ai_service):
    """Mock all external services."""
    with patch('backend.app.services.airspace_service.AirspaceService') as airspace_mock:
        airspace_mock.return_value.check_airspace.return_value = {
            "restrictions": [],
            "warnings": [],
            "flight_allowed": True
        }
        
        yield {
            'weather': mock_weather_service,
            'ai': mock_ai_service,
            'airspace': airspace_mock
        }


@pytest.fixture
def performance_monitor():
    """Performance monitoring fixture."""
    from backend.app.core.monitoring import PerformanceMonitor
    
    monitor = PerformanceMonitor()
    return monitor


@pytest.fixture
def metrics_collector():
    """Metrics collector fixture."""
    from backend.app.core.monitoring import MetricsCollector
    
    collector = MetricsCollector()
    return collector


class DatabaseTestCase:
    """Base test case for database operations."""
    
    def setup_method(self):
        """Set up test method."""
        self.db_session_started = False
    
    def teardown_method(self):
        """Clean up after test method."""
        if self.db_session_started:
            # Cleanup logic here
            pass


class APITestCase:
    """Base test case for API testing."""
    
    def make_request(
        self,
        client: FlaskClient,
        method: str,
        url: str,
        data: Optional[Dict] = None,
        headers: Optional[Dict] = None,
        expected_status: int = 200
    ):
        """Make API request with validation."""
        if headers is None:
            headers = {'Content-Type': 'application/json'}
        
        if method.upper() == 'GET':
            response = client.get(url, headers=headers)
        elif method.upper() == 'POST':
            response = client.post(url, json=data, headers=headers)
        elif method.upper() == 'PUT':
            response = client.put(url, json=data, headers=headers)
        elif method.upper() == 'DELETE':
            response = client.delete(url, headers=headers)
        else:
            raise ValueError(f"Unsupported HTTP method: {method}")
        
        assert response.status_code == expected_status, \
            f"Expected status {expected_status}, got {response.status_code}. Response: {response.get_json()}"
        
        return response


class ServiceTestCase:
    """Base test case for service testing."""
    
    def setup_method(self):
        """Set up service test."""
        self.service_registry = ServiceRegistry()
    
    def register_mock_service(self, service_name: str, mock_service):
        """Register mock service for testing."""
        self.service_registry.register_service(mock_service, service_name)


@pytest.fixture
def database_test_case():
    """Database test case fixture."""
    return DatabaseTestCase()


@pytest.fixture
def api_test_case():
    """API test case fixture."""
    return APITestCase()


@pytest.fixture
def service_test_case():
    """Service test case fixture."""
    return ServiceTestCase()


# Performance testing utilities
class PerformanceTestUtils:
    """Utilities for performance testing."""
    
    @staticmethod
    def measure_response_time(func, *args, **kwargs):
        """Measure function execution time."""
        import time
        start_time = time.time()
        result = func(*args, **kwargs)
        end_time = time.time()
        return result, end_time - start_time
    
    @staticmethod
    def load_test(func, iterations: int = 100, concurrent: bool = False):
        """Simple load testing utility."""
        import concurrent.futures
        import time
        
        results = []
        start_time = time.time()
        
        if concurrent:
            with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
                futures = [executor.submit(func) for _ in range(iterations)]
                results = [future.result() for future in concurrent.futures.as_completed(futures)]
        else:
            results = [func() for _ in range(iterations)]
        
        end_time = time.time()
        
        return {
            "total_time": end_time - start_time,
            "iterations": iterations,
            "avg_time_per_iteration": (end_time - start_time) / iterations,
            "results": results
        }


@pytest.fixture
def performance_utils():
    """Performance testing utilities fixture."""
    return PerformanceTestUtils()


# Async testing support
@pytest.fixture
def event_loop():
    """Create event loop for async testing."""
    import asyncio
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


# Configuration for test discovery
def pytest_configure(config):
    """Configure pytest settings."""
    # Add custom markers
    config.addinivalue_line(
        "markers", "unit: mark test as unit test"
    )
    config.addinivalue_line(
        "markers", "integration: mark test as integration test"
    )
    config.addinivalue_line(
        "markers", "performance: mark test as performance test"
    )
    config.addinivalue_line(
        "markers", "slow: mark test as slow running"
    )


def pytest_collection_modifyitems(config, items):
    """Modify test collection."""
    # Automatically mark tests based on their path
    for item in items:
        # Mark unit tests
        if "unit" in str(item.fspath):
            item.add_marker(pytest.mark.unit)
        
        # Mark integration tests
        if "integration" in str(item.fspath):
            item.add_marker(pytest.mark.integration)
        
        # Mark performance tests
        if "performance" in str(item.fspath):
            item.add_marker(pytest.mark.performance)


# Test data generators
class TestDataFactory:
    """Factory for generating test data."""
    
    @staticmethod
    def create_drone(override_data: Optional[Dict] = None) -> Dict[str, Any]:
        """Create drone test data."""
        base_data = {
            "name": f"Test Drone {datetime.utcnow().timestamp()}",
            "status": "available",
            "battery_percentage": 100.0,
            "location": {
                "latitude": 37.7749,
                "longitude": -122.4194,
                "altitude": 0.0
            }
        }
        
        if override_data:
            base_data.update(override_data)
        
        return base_data
    
    @staticmethod
    def create_mission(override_data: Optional[Dict] = None) -> Dict[str, Any]:
        """Create mission test data."""
        base_data = {
            "name": f"Test Mission {datetime.utcnow().timestamp()}",
            "status": "planned",
            "altitude_m": 100.0,
            "overlap_percentage": 60.0,
            "survey_area": {
                "type": "Polygon",
                "coordinates": [[
                    [-122.4194, 37.7749],
                    [-122.4094, 37.7749],
                    [-122.4094, 37.7649],
                    [-122.4194, 37.7649],
                    [-122.4194, 37.7749]
                ]]
            }
        }
        
        if override_data:
            base_data.update(override_data)
        
        return base_data


@pytest.fixture
def test_data_factory():
    """Test data factory fixture."""
    return TestDataFactory()
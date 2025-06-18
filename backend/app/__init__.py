"""
Flask application factory for the Drone Survey Management System.

This module contains the application factory function that creates
and configures the Flask application with all necessary extensions,
blueprints, and middleware.
"""

import os
from flask import Flask
from flask_cors import CORS
from flask_socketio import SocketIO
from config import config_mapping

# Initialize extensions
socketio = SocketIO()


def create_app(config_name=None):
    """
    Application factory function to create and configure Flask app.
    
    Args:
        config_name (str, optional): Configuration environment name.
                                   Defaults to 'development'.
    
    Returns:
        Flask: Configured Flask application instance
    """
    # Determine configuration
    if config_name is None:
        config_name = os.environ.get('FLASK_ENV', 'development')
    
    # Create Flask application
    app = Flask(__name__)
    
    # Load configuration
    config_class = config_mapping.get(config_name, config_mapping['default'])
    app.config.from_object(config_class)
    
    # Initialize extensions with app
    from .models import db
    db.init_app(app)
    
    # Configure CORS
    CORS(app, origins=app.config['CORS_ORIGINS'])
    
    # Configure SocketIO
    socketio.init_app(
        app,
        cors_allowed_origins=app.config['SOCKETIO_CORS_ALLOWED_ORIGINS'],
        ping_timeout=app.config['SOCKETIO_PING_TIMEOUT'],
        ping_interval=app.config['SOCKETIO_PING_INTERVAL']
    )    
    # Register blueprints
    from .blueprints import drones_bp, missions_bp, reports_bp
    app.register_blueprint(drones_bp, url_prefix='/api/v1/drones')
    app.register_blueprint(missions_bp, url_prefix='/api/v1/missions')
    app.register_blueprint(reports_bp, url_prefix='/api/v1/reports')
    
    # Register WebSocket handlers
    from .websockets import register_websocket_handlers
    register_websocket_handlers(socketio)
    
    # Create database tables
    with app.app_context():
        db.create_all()
        
        # Create some sample data in development
        if app.config.get('DEVELOPMENT', False):
            create_sample_data(db)
    
    # Health check endpoint
    @app.route('/health')
    def health_check():
        """Basic health check endpoint for monitoring."""
        return {'status': 'healthy', 'service': 'drone-survey-backend'}
    
    # API info endpoint
    @app.route('/api/v1')
    def api_info():
        """API information endpoint."""
        return {
            'name': 'Drone Survey Management System API',
            'version': '1.0.0',
            'endpoints': {
                'drones': '/api/v1/drones',
                'missions': '/api/v1/missions', 
                'reports': '/api/v1/reports'
            }
        }
    
    return app


def create_sample_data(db):
    """
    Create sample data for development environment.
    
    Args:
        db: SQLAlchemy database instance
    """
    from .models import Drone, Mission, DroneStatus, MissionStatus, SurveyPattern
    import json
    
    # Check if data already exists
    if Drone.query.first() is not None:
        return
    
    # Create sample drones
    drones = [
        Drone(
            name="Alpha-01",
            model="DJI Matrice 300 RTK",
            serial_number="DJI001",
            status=DroneStatus.AVAILABLE,
            battery_percentage=85.0,
            current_location_lat=37.7749,
            current_location_lng=-122.4194,
            flight_hours_total=124.5
        ),
        Drone(
            name="Beta-02", 
            model="DJI Phantom 4 RTK",
            serial_number="DJI002",
            status=DroneStatus.AVAILABLE,
            battery_percentage=92.0,
            current_location_lat=37.7849,
            current_location_lng=-122.4094,
            flight_hours_total=67.2
        ),
        Drone(
            name="Gamma-03",
            model="Autel EVO II Pro RTK",
            serial_number="AUT001", 
            status=DroneStatus.MAINTENANCE,
            battery_percentage=15.0,
            flight_hours_total=234.1
        )
    ]
    
    for drone in drones:
        db.session.add(drone)
    
    db.session.commit()
    
    # Create sample mission
    sample_area = {
        "type": "Polygon",
        "coordinates": [[
            [-122.4194, 37.7749],
            [-122.4094, 37.7749], 
            [-122.4094, 37.7649],
            [-122.4194, 37.7649],
            [-122.4194, 37.7749]
        ]]
    }
    
    mission = Mission(
        name="Golden Gate Park Survey",
        description="Aerial survey of Golden Gate Park for vegetation analysis",
        status=MissionStatus.PLANNED,
        survey_area_geojson=json.dumps(sample_area),
        altitude_m=50.0,
        overlap_percentage=30.0,
        survey_pattern=SurveyPattern.CROSSHATCH,
        estimated_duration_minutes=45
    )
    
    db.session.add(mission)
    db.session.commit()
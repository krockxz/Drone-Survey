#!/usr/bin/env python3
"""
Application Entry Point for Drone Survey Management System.

This script creates and runs the Flask application with WebSocket support,
database initialization, and proper configuration management.

Usage:
    python run.py [--config CONFIG] [--host HOST] [--port PORT] [--debug]

Author: FlytBase Assignment
Created: 2024
"""

import os
import sys
import argparse
import logging
from flask import Flask
from flask_socketio import SocketIO

# Add current directory to Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from config import get_config, validate_config
from app.models import db, init_db
from app.blueprints.drones import drones_bp
from app.blueprints.simulator import simulator_bp
from app.websockets.mission_updates import init_websockets


def create_app(config_name: str = None) -> tuple[Flask, SocketIO]:
    """Create and configure Flask application with WebSocket support.
    
    Args:
        config_name: Configuration environment name
        
    Returns:
        tuple: (Flask app, SocketIO instance)
    """
    # Create Flask application
    app = Flask(__name__)
    
    # Load configuration
    if config_name is None:
        config_name = os.environ.get('FLASK_ENV', 'development')
    
    config_class = get_config(config_name)
    app.config.from_object(config_class)
    
    # Validate configuration
    try:
        validate_config(app.config)
    except ValueError as e:
        app.logger.error(f"Configuration validation failed: {e}")
        sys.exit(1)
    
    # Initialize configuration
    config_class.init_app(app)
    
    # Initialize database
    db.init_app(app)
    
    # Create SocketIO instance
    socketio = SocketIO(
        app,
        cors_allowed_origins=app.config['SOCKETIO_CORS_ALLOWED_ORIGINS'],
        async_mode=app.config['SOCKETIO_ASYNC_MODE'],
        ping_timeout=app.config['SOCKETIO_PING_TIMEOUT'],
        ping_interval=app.config['SOCKETIO_PING_INTERVAL']
    )
    
    # Initialize WebSocket handlers
    init_websockets(socketio)
    
    # Register blueprints
    app.register_blueprint(drones_bp)
    app.register_blueprint(simulator_bp)
    
    # Health check endpoint
    @app.route('/health')
    def health_check():
        """Health check endpoint for monitoring."""
        return {
            'status': 'healthy',
            'service': 'drone-survey-backend',
            'version': '1.0.0'
        }
    
    # API info endpoint
    @app.route('/api/v1')
    def api_info():
        """API information endpoint."""
        return {
            'service': 'Drone Survey Management System API',
            'version': 'v1',
            'endpoints': {
                'drones': '/api/v1/drones',
                'simulator': '/api/v1/simulator',
                'health': '/health'
            },
            'websocket': {
                'enabled': True,
                'events': [
                    'drone_status_update',
                    'mission_progress_update',
                    'fleet_summary',
                    'emergency_alert'
                ]
            }
        }
    
    # Initialize database tables
    with app.app_context():
        init_db(app)
    
    return app, socketio


def main():
    """Main entry point for the application."""
    parser = argparse.ArgumentParser(description='Drone Survey Management System')
    parser.add_argument('--config', default=None,
                       help='Configuration environment (development, production, testing)')
    parser.add_argument('--host', default='localhost',
                       help='Host to bind to (default: localhost)')
    parser.add_argument('--port', type=int, default=5000,
                       help='Port to bind to (default: 5000)')
    parser.add_argument('--debug', action='store_true',
                       help='Enable debug mode')
    
    args = parser.parse_args()
    
    try:
        # Create application
        app, socketio = create_app(args.config)
        
        # Override debug mode if specified
        if args.debug:
            app.config['DEBUG'] = True
        
        print("🚁 Drone Survey Management System")
        print("=" * 50)
        print(f"🔧 Environment: {app.config.get('FLASK_ENV', 'development')}")
        print(f"🗄️  Database: {app.config['SQLALCHEMY_DATABASE_URI'][:50]}...")
        print(f"🌐 Server: http://{args.host}:{args.port}")
        print(f"📡 WebSocket: Enabled")
        print(f"🐛 Debug Mode: {app.config.get('DEBUG', False)}")
        print("=" * 50)
        print("📊 API Endpoints:")
        print(f"   Health Check: http://{args.host}:{args.port}/health")
        print(f"   API Info: http://{args.host}:{args.port}/api/v1")
        print(f"   Drones: http://{args.host}:{args.port}/api/v1/drones")
        print(f"   Simulator: http://{args.host}:{args.port}/api/v1/simulator")
        print("=" * 50)
        print("🚀 Starting server...")
        print("⌨️  Press Ctrl+C to stop")
        print()
        
        # Run application with SocketIO
        socketio.run(
            app,
            host=args.host,
            port=args.port,
            debug=app.config.get('DEBUG', False),
            use_reloader=False  # Disable reloader to prevent issues with SocketIO
        )
        
    except KeyboardInterrupt:
        print("\n⏹️ Server stopped by user")
    except Exception as e:
        print(f"❌ Failed to start server: {e}")
        sys.exit(1)


if __name__ == '__main__':
    main()
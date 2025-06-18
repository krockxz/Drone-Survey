"""
Configuration module for the Drone Survey Management System.

This module provides environment-based configuration management supporting
development, testing, and production environments with appropriate defaults
and security considerations.

Author: FlytBase Assignment
Created: 2024
"""

import os
from typing import Dict, Any, Optional
from urllib.parse import urlparse


class Config:
    """Base configuration class with common settings.
    
    Contains default values and common configuration parameters that are
    shared across all environments. Environment-specific classes inherit
    from this base class and override specific settings.
    """
    
    # Application Core Settings
    SECRET_KEY: str = os.environ.get('SECRET_KEY') or 'dev-secret-key-change-in-production'
    
    # Database Configuration
    SQLALCHEMY_DATABASE_URI: str = os.environ.get('DATABASE_URL') or 'sqlite:///drone_survey.db'
    SQLALCHEMY_TRACK_MODIFICATIONS: bool = False
    SQLALCHEMY_ECHO: bool = False
    
    # Flask-SocketIO Configuration
    SOCKETIO_ASYNC_MODE: str = 'eventlet'
    SOCKETIO_CORS_ALLOWED_ORIGINS: str = os.environ.get('CORS_ORIGINS', '*')
    SOCKETIO_PING_TIMEOUT: int = 60
    SOCKETIO_PING_INTERVAL: int = 25
    
    # API Configuration
    API_VERSION: str = 'v1'
    API_PREFIX: str = f'/api/{API_VERSION}'
    
    # Pagination Settings
    DEFAULT_PAGE_SIZE: int = 20
    MAX_PAGE_SIZE: int = 100
    
    # Mission Configuration
    MAX_MISSION_DURATION_HOURS: int = 8
    DEFAULT_ALTITUDE_M: float = 100.0
    MIN_ALTITUDE_M: float = 30.0
    MAX_ALTITUDE_M: float = 400.0
    DEFAULT_OVERLAP_PERCENTAGE: float = 60.0
    
    # Drone Configuration
    BATTERY_LOW_THRESHOLD: float = 20.0
    BATTERY_CRITICAL_THRESHOLD: float = 10.0
    MAX_FLIGHT_TIME_MINUTES: int = 25
    
    # Real-time Update Intervals (seconds)
    DRONE_STATUS_UPDATE_INTERVAL: int = 5
    MISSION_PROGRESS_UPDATE_INTERVAL: int = 3
    FLEET_SUMMARY_UPDATE_INTERVAL: int = 10
    
    # File Upload Configuration
    MAX_CONTENT_LENGTH: int = 16 * 1024 * 1024  # 16MB
    UPLOAD_FOLDER: str = os.environ.get('UPLOAD_FOLDER', 'uploads')
    
    # Logging Configuration
    LOG_LEVEL: str = os.environ.get('LOG_LEVEL', 'INFO')
    LOG_FORMAT: str = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    
    # Security Settings
    CORS_ORIGINS: list = os.environ.get('CORS_ORIGINS', 'http://localhost:5173').split(',')
    CSRF_ENABLED: bool = True
    
    # Cache Configuration (Redis support ready)
    CACHE_TYPE: str = os.environ.get('CACHE_TYPE', 'simple')
    CACHE_DEFAULT_TIMEOUT: int = 300
    REDIS_URL: Optional[str] = os.environ.get('REDIS_URL')
    
    @staticmethod
    def init_app(app) -> None:
        """Initialize application with configuration.
        
        Args:
            app: Flask application instance to configure.
        """
        pass


class DevelopmentConfig(Config):
    """Development environment configuration.
    
    Optimized for development with debugging enabled, verbose logging,
    and development-friendly database settings.
    """
    
    DEBUG: bool = True
    TESTING: bool = False
    SQLALCHEMY_ECHO: bool = True
    LOG_LEVEL: str = 'DEBUG'
    
    # Development-specific WebSocket settings
    SOCKETIO_CORS_ALLOWED_ORIGINS: str = '*'
    
    # Development database with detailed logging
    SQLALCHEMY_DATABASE_URI: str = (
        os.environ.get('DEV_DATABASE_URL') or 
        'sqlite:///drone_survey_dev.db'
    )
    
    @staticmethod
    def init_app(app) -> None:
        """Initialize development application.
        
        Args:
            app: Flask application instance.
        """
        import logging
        logging.basicConfig(level=logging.DEBUG)
        print("🚁 Drone Survey System - Development Mode")


class TestingConfig(Config):
    """Testing environment configuration.
    
    Configured for unit tests, integration tests, and CI/CD pipelines
    with in-memory database and simplified settings.
    """
    
    TESTING: bool = True
    DEBUG: bool = True
    WTF_CSRF_ENABLED: bool = False
    
    # In-memory database for testing
    SQLALCHEMY_DATABASE_URI: str = 'sqlite:///:memory:'
    
    # Reduced timeouts for faster tests
    SOCKETIO_PING_TIMEOUT: int = 10
    SOCKETIO_PING_INTERVAL: int = 5
    
    # Test-specific intervals
    DRONE_STATUS_UPDATE_INTERVAL: int = 1
    MISSION_PROGRESS_UPDATE_INTERVAL: int = 1
    
    @staticmethod
    def init_app(app) -> None:
        """Initialize testing application.
        
        Args:
            app: Flask application instance.
        """
        import logging
        logging.disable(logging.CRITICAL)


class ProductionConfig(Config):
    """Production environment configuration.
    
    Security-hardened configuration for production deployment with
    PostgreSQL support, enhanced logging, and production optimizations.
    """
    
    DEBUG: bool = False
    TESTING: bool = False
    
    # Production database (PostgreSQL recommended)
    SQLALCHEMY_DATABASE_URI: str = (
        os.environ.get('DATABASE_URL') or 
        'postgresql://user:password@localhost/drone_survey_prod'
    )
    
    # Enhanced security
    SECRET_KEY: str = os.environ.get('SECRET_KEY')
    CSRF_ENABLED: bool = True
    
    # Production WebSocket settings
    SOCKETIO_CORS_ALLOWED_ORIGINS: str = os.environ.get(
        'CORS_ORIGINS', 
        'https://yourdomain.com'
    )
    
    # Production optimizations
    SQLALCHEMY_ENGINE_OPTIONS: Dict[str, Any] = {
        'pool_pre_ping': True,
        'pool_recycle': 3600,
        'pool_size': 10,
        'max_overflow': 20
    }
    
    @staticmethod
    def init_app(app) -> None:
        """Initialize production application.
        
        Args:
            app: Flask application instance.
        """
        import logging
        from logging.handlers import RotatingFileHandler
        
        # Production logging setup
        if not app.debug and not app.testing:
            if not os.path.exists('logs'):
                os.mkdir('logs')
            
            file_handler = RotatingFileHandler(
                'logs/drone_survey.log',
                maxBytes=10240000,  # 10MB
                backupCount=10
            )
            file_handler.setFormatter(logging.Formatter(Config.LOG_FORMAT))
            file_handler.setLevel(logging.INFO)
            app.logger.addHandler(file_handler)
            
            app.logger.setLevel(logging.INFO)
            app.logger.info('🚁 Drone Survey System - Production Mode')
        
        # Validate critical production settings
        if not os.environ.get('SECRET_KEY'):
            raise ValueError("SECRET_KEY environment variable must be set in production")


class DockerConfig(ProductionConfig):
    """Docker deployment configuration.
    
    Specialized configuration for containerized deployment with
    appropriate networking and volume mount settings.
    """
    
    # Docker-specific database URL parsing
    @classmethod
    def get_database_uri(cls) -> str:
        """Parse database URL for Docker environment.
        
        Returns:
            str: Properly formatted database URI for Docker networking.
        """
        database_url = os.environ.get('DATABASE_URL')
        if database_url and database_url.startswith('postgres://'):
            # Convert postgres:// to postgresql:// for SQLAlchemy compatibility
            database_url = database_url.replace('postgres://', 'postgresql://', 1)
        return database_url or cls.SQLALCHEMY_DATABASE_URI
    
    SQLALCHEMY_DATABASE_URI: str = get_database_uri()
    
    # Docker networking considerations
    SOCKETIO_CORS_ALLOWED_ORIGINS: str = os.environ.get('CORS_ORIGINS', '*')
    
    @staticmethod
    def init_app(app) -> None:
        """Initialize Docker application.
        
        Args:
            app: Flask application instance.
        """
        ProductionConfig.init_app(app)
        
        # Docker-specific logging to stdout
        import logging
        import sys
        
        stream_handler = logging.StreamHandler(sys.stdout)
        stream_handler.setFormatter(logging.Formatter(Config.LOG_FORMAT))
        app.logger.addHandler(stream_handler)
        app.logger.info('🚁 Drone Survey System - Docker Mode')


# Configuration mapping for easy environment switching
config: Dict[str, Config] = {
    'development': DevelopmentConfig,
    'testing': TestingConfig,
    'production': ProductionConfig,
    'docker': DockerConfig,
    'default': DevelopmentConfig
}


def get_config(environment: Optional[str] = None) -> Config:
    """Get configuration class for specified environment.
    
    Args:
        environment: Environment name. If None, uses FLASK_ENV or defaults to 'development'.
        
    Returns:
        Config: Configuration class instance for the specified environment.
        
    Raises:
        ValueError: If the specified environment is not supported.
    """
    if environment is None:
        environment = os.environ.get('FLASK_ENV', 'development')
    
    if environment not in config:
        raise ValueError(f"Unsupported environment: {environment}")
    
    return config[environment]


def validate_config(config_obj: Config) -> bool:
    """Validate configuration settings.
    
    Args:
        config_obj: Configuration object to validate.
        
    Returns:
        bool: True if configuration is valid.
        
    Raises:
        ValueError: If critical configuration is missing or invalid.
    """
    # Validate database URI
    if not config_obj.SQLALCHEMY_DATABASE_URI:
        raise ValueError("Database URI must be configured")
    
    # Validate secret key in production
    if (not config_obj.DEBUG and 
        config_obj.SECRET_KEY == 'dev-secret-key-change-in-production'):
        raise ValueError("Production secret key must be set")
    
    # Validate altitude limits
    if config_obj.MIN_ALTITUDE_M >= config_obj.MAX_ALTITUDE_M:
        raise ValueError("Invalid altitude configuration")
    
    # Validate battery thresholds
    if config_obj.BATTERY_CRITICAL_THRESHOLD >= config_obj.BATTERY_LOW_THRESHOLD:
        raise ValueError("Invalid battery threshold configuration")
    
    return True


# Export configuration getter for application factory
__all__ = ['config', 'get_config', 'validate_config']
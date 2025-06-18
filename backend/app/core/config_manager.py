"""
Enterprise Configuration Manager

Centralized configuration management with environment validation,
secret handling, and runtime configuration updates.

Author: FlytBase Assignment - Enterprise Edition
Created: 2024
"""

import os
import logging
from typing import Dict, Any, Optional, Type
from pathlib import Path
from dotenv import load_dotenv

from .config_schema import DroneSurveyConfig, validate_config


class ConfigurationManager:
    """
    Enterprise-grade configuration manager with validation,
    secret management, and environment-specific handling.
    """
    
    _instance: Optional['ConfigurationManager'] = None
    _config: Optional[DroneSurveyConfig] = None
    
    def __new__(cls) -> 'ConfigurationManager':
        """Singleton pattern for configuration manager."""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(self):
        """Initialize configuration manager."""
        if self._config is None:
            self._load_environment()
            self._config = self._create_config()
            self._validate_configuration()
    
    def _load_environment(self) -> None:
        """Load environment variables from .env files."""
        # Determine environment
        environment = os.getenv('FLASK_ENV', 'development')
        
        # Load environment-specific .env file
        env_files = [
            f'.env.{environment}',
            '.env.local',
            '.env'
        ]
        
        for env_file in env_files:
            env_path = Path(env_file)
            if env_path.exists():
                load_dotenv(env_path, override=True)
                logging.info(f"Loaded environment from {env_file}")
    
    def _create_config(self) -> DroneSurveyConfig:
        """Create and return configuration instance."""
        try:
            config = DroneSurveyConfig()
            logging.info(f"Configuration loaded for environment: {config.environment}")
            return config
        except Exception as e:
            logging.error(f"Failed to create configuration: {e}")
            raise
    
    def _validate_configuration(self) -> None:
        """Validate configuration and log warnings/errors."""
        if self._config is None:
            return
        
        validation_results = validate_config(self._config)
        
        if not validation_results["valid"]:
            for error in validation_results["errors"]:
                logging.error(f"Configuration error: {error}")
            raise ValueError("Invalid configuration detected")
        
        for warning in validation_results["warnings"]:
            logging.warning(f"Configuration warning: {warning}")
    
    @property
    def config(self) -> DroneSurveyConfig:
        """Get the current configuration."""
        if self._config is None:
            raise RuntimeError("Configuration not initialized")
        return self._config
    
    def reload_config(self) -> None:
        """Reload configuration from environment variables."""
        logging.info("Reloading configuration...")
        self._load_environment()
        self._config = self._create_config()
        self._validate_configuration()
        logging.info("Configuration reloaded successfully")
    
    def get_database_config(self) -> Dict[str, Any]:
        """Get database configuration for SQLAlchemy."""
        db_config = self.config.database
        
        return {
            'SQLALCHEMY_DATABASE_URI': str(db_config.url),
            'SQLALCHEMY_TRACK_MODIFICATIONS': False,
            'SQLALCHEMY_ECHO': db_config.echo,
            'SQLALCHEMY_ENGINE_OPTIONS': {
                'pool_size': db_config.pool_size,
                'max_overflow': db_config.max_overflow,
                'pool_recycle': db_config.pool_recycle,
                'pool_pre_ping': db_config.pool_pre_ping,
            }
        }
    
    def get_flask_config(self) -> Dict[str, Any]:
        """Get Flask-specific configuration."""
        config = self.config
        
        flask_config = {
            'SECRET_KEY': config.security.secret_key.get_secret_value(),
            'DEBUG': config.debug,
            'TESTING': config.testing,
            'HOST': config.host,
            'PORT': config.port,
        }
        
        # Add database configuration
        flask_config.update(self.get_database_config())
        
        # Add security configuration
        flask_config.update({
            'JWT_SECRET_KEY': config.security.jwt_secret_key.get_secret_value(),
            'JWT_ACCESS_TOKEN_EXPIRES': config.security.jwt_access_token_expires,
            'JWT_REFRESH_TOKEN_EXPIRES': config.security.jwt_refresh_token_expires,
            'WTF_CSRF_ENABLED': config.security.csrf_enabled,
        })
        
        # Add cache configuration
        if config.cache.type == 'redis' and config.cache.redis_url:
            flask_config['CACHE_TYPE'] = 'redis'
            flask_config['CACHE_REDIS_URL'] = str(config.cache.redis_url)
            if config.cache.redis_password:
                flask_config['CACHE_REDIS_PASSWORD'] = config.cache.redis_password.get_secret_value()
        else:
            flask_config['CACHE_TYPE'] = 'simple'
        
        flask_config['CACHE_DEFAULT_TIMEOUT'] = config.cache.default_timeout
        
        return flask_config
    
    def get_socketio_config(self) -> Dict[str, Any]:
        """Get SocketIO configuration."""
        return {
            'cors_allowed_origins': self.config.cors_origins,
            'async_mode': 'eventlet',
            'ping_timeout': 60,
            'ping_interval': 25,
        }
    
    def get_logging_config(self) -> Dict[str, Any]:
        """Get logging configuration."""
        log_config = self.config.logging
        
        return {
            'level': log_config.level,
            'format': log_config.format,
            'file_max_size': log_config.file_max_size,
            'file_backup_count': log_config.file_backup_count,
            'structured_logging': log_config.structured_logging,
            'apm_enabled': log_config.apm_enabled,
            'apm_service_name': log_config.apm_service_name,
            'apm_server_url': str(log_config.apm_server_url) if log_config.apm_server_url else None,
            'apm_secret_token': log_config.apm_secret_token.get_secret_value() if log_config.apm_secret_token else None,
        }
    
    def is_feature_enabled(self, feature_name: str) -> bool:
        """Check if a feature flag is enabled."""
        features = self.config.features
        return getattr(features, feature_name, False)
    
    def get_external_service_config(self, service_name: str) -> Optional[Dict[str, Any]]:
        """Get configuration for external service."""
        external = self.config.external_services
        
        service_configs = {
            'weather': {
                'api_key': external.weather_api_key.get_secret_value() if external.weather_api_key else None,
                'api_url': str(external.weather_api_url),
            },
            'mapbox': {
                'access_token': external.mapbox_access_token.get_secret_value() if external.mapbox_access_token else None,
            },
            'google_maps': {
                'api_key': external.google_maps_api_key.get_secret_value() if external.google_maps_api_key else None,
            },
            'airspace': {
                'api_key': external.airspace_api_key.get_secret_value() if external.airspace_api_key else None,
                'notam_url': str(external.notam_api_url),
            },
            'ai_model': {
                'endpoint': str(external.ai_model_endpoint) if external.ai_model_endpoint else None,
                'api_key': external.ai_model_api_key.get_secret_value() if external.ai_model_api_key else None,
                'optimization_enabled': external.ai_optimization_enabled,
                'confidence_threshold': external.ai_prediction_confidence_threshold,
            }
        }
        
        return service_configs.get(service_name)
    
    def export_config(self, include_secrets: bool = False) -> Dict[str, Any]:
        """Export configuration for debugging/documentation."""
        config_dict = self.config.dict()
        
        if not include_secrets:
            # Remove sensitive information
            self._redact_secrets(config_dict)
        
        return config_dict
    
    def _redact_secrets(self, config_dict: Dict[str, Any]) -> None:
        """Redact sensitive information from configuration."""
        sensitive_keys = [
            'secret_key', 'jwt_secret_key', 'csrf_secret_key',
            'password', 'api_key', 'access_token', 'auth_token'
        ]
        
        def redact_recursive(obj):
            if isinstance(obj, dict):
                for key, value in obj.items():
                    if any(sensitive in key.lower() for sensitive in sensitive_keys):
                        obj[key] = "***REDACTED***"
                    else:
                        redact_recursive(value)
            elif isinstance(obj, list):
                for item in obj:
                    redact_recursive(item)
        
        redact_recursive(config_dict)


# Global configuration manager instance
_config_manager: Optional[ConfigurationManager] = None


def get_config_manager() -> ConfigurationManager:
    """Get the global configuration manager instance."""
    global _config_manager
    if _config_manager is None:
        _config_manager = ConfigurationManager()
    return _config_manager


def get_config() -> DroneSurveyConfig:
    """Get the current configuration."""
    return get_config_manager().config


def reload_config() -> None:
    """Reload configuration from environment."""
    get_config_manager().reload_config()


# Convenience functions for common configuration access
def get_database_config() -> Dict[str, Any]:
    """Get database configuration."""
    return get_config_manager().get_database_config()


def get_flask_config() -> Dict[str, Any]:
    """Get Flask configuration."""
    return get_config_manager().get_flask_config()


def is_feature_enabled(feature_name: str) -> bool:
    """Check if a feature is enabled."""
    return get_config_manager().is_feature_enabled(feature_name)


def get_external_service_config(service_name: str) -> Optional[Dict[str, Any]]:
    """Get external service configuration."""
    return get_config_manager().get_external_service_config(service_name)
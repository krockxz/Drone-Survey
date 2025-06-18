"""
Enterprise Configuration Schema and Validation

This module provides Pydantic-based configuration validation ensuring
type safety, validation, and comprehensive error reporting for all
configuration parameters across different environments.

Author: FlytBase Assignment - Enterprise Edition
Created: 2024
"""

from typing import List, Optional, Literal, Union, Dict, Any
from pydantic import BaseSettings, validator, Field, SecretStr
from pydantic.networks import HttpUrl, PostgresDsn, RedisDsn
import os
from pathlib import Path


class DatabaseConfig(BaseSettings):
    """Database configuration with validation and connection pooling."""
    
    url: PostgresDsn = Field(
        default="sqlite:///drone_survey.db",
        description="Database connection URL"
    )
    pool_size: int = Field(
        default=10,
        ge=1,
        le=50,
        description="Database connection pool size"
    )
    max_overflow: int = Field(
        default=20,
        ge=0,
        le=100,
        description="Maximum overflow connections"
    )
    pool_recycle: int = Field(
        default=3600,
        ge=300,
        description="Pool recycle time in seconds"
    )
    pool_pre_ping: bool = Field(
        default=True,
        description="Enable connection health checks"
    )
    echo: bool = Field(
        default=False,
        description="Enable SQL query logging"
    )
    
    class Config:
        env_prefix = "DB_"


class SecurityConfig(BaseSettings):
    """Security configuration with encryption and authentication settings."""
    
    secret_key: SecretStr = Field(
        ...,
        min_length=32,
        description="Application secret key for encryption"
    )
    jwt_secret_key: SecretStr = Field(
        ...,
        min_length=32,
        description="JWT token signing key"
    )
    jwt_access_token_expires: int = Field(
        default=3600,
        ge=300,
        le=86400,
        description="JWT access token expiration in seconds"
    )
    jwt_refresh_token_expires: int = Field(
        default=2592000,
        ge=3600,
        description="JWT refresh token expiration in seconds"
    )
    csrf_enabled: bool = Field(
        default=True,
        description="Enable CSRF protection"
    )
    csrf_secret_key: Optional[SecretStr] = Field(
        default=None,
        description="CSRF protection secret key"
    )
    rate_limit_enabled: bool = Field(
        default=True,
        description="Enable API rate limiting"
    )
    rate_limit_default: str = Field(
        default="100 per hour",
        description="Default rate limit for API endpoints"
    )
    session_cookie_secure: bool = Field(
        default=True,
        description="Use secure cookies (HTTPS only)"
    )
    session_cookie_httponly: bool = Field(
        default=True,
        description="HTTP-only session cookies"
    )
    session_cookie_samesite: Literal["Strict", "Lax", "None"] = Field(
        default="Lax",
        description="SameSite cookie policy"
    )
    
    @validator('csrf_secret_key', always=True)
    def set_csrf_secret(cls, v, values):
        """Set CSRF secret key if not provided."""
        if v is None and values.get('csrf_enabled'):
            return values.get('secret_key')
        return v
    
    class Config:
        env_prefix = "SECURITY_"


class CacheConfig(BaseSettings):
    """Cache configuration supporting Redis and in-memory caching."""
    
    type: Literal["simple", "redis", "memcached"] = Field(
        default="simple",
        description="Cache backend type"
    )
    default_timeout: int = Field(
        default=300,
        ge=1,
        description="Default cache timeout in seconds"
    )
    redis_url: Optional[RedisDsn] = Field(
        default=None,
        description="Redis connection URL"
    )
    redis_password: Optional[SecretStr] = Field(
        default=None,
        description="Redis authentication password"
    )
    redis_db: int = Field(
        default=0,
        ge=0,
        le=15,
        description="Redis database number"
    )
    
    @validator('redis_url')
    def validate_redis_config(cls, v, values):
        """Validate Redis configuration when Redis cache is selected."""
        if values.get('type') == 'redis' and v is None:
            raise ValueError("Redis URL is required when using Redis cache")
        return v
    
    class Config:
        env_prefix = "CACHE_"


class ExternalServicesConfig(BaseSettings):
    """Configuration for external service integrations."""
    
    # Weather Services
    weather_api_key: Optional[SecretStr] = Field(
        default=None,
        description="Weather API key"
    )
    weather_api_url: HttpUrl = Field(
        default="https://api.openweathermap.org/data/2.5",
        description="Weather API base URL"
    )
    
    # Mapping Services
    mapbox_access_token: Optional[SecretStr] = Field(
        default=None,
        description="Mapbox access token"
    )
    google_maps_api_key: Optional[SecretStr] = Field(
        default=None,
        description="Google Maps API key"
    )
    
    # Airspace Services
    airspace_api_key: Optional[SecretStr] = Field(
        default=None,
        description="Airspace monitoring API key"
    )
    notam_api_url: HttpUrl = Field(
        default="https://api.faa.gov/notam",
        description="NOTAM API endpoint"
    )
    
    # AI/ML Services
    ai_model_endpoint: Optional[HttpUrl] = Field(
        default=None,
        description="AI model inference endpoint"
    )
    ai_model_api_key: Optional[SecretStr] = Field(
        default=None,
        description="AI model API key"
    )
    ai_optimization_enabled: bool = Field(
        default=True,
        description="Enable AI optimization features"
    )
    ai_prediction_confidence_threshold: float = Field(
        default=0.85,
        ge=0.0,
        le=1.0,
        description="Minimum confidence threshold for AI predictions"
    )
    
    class Config:
        env_prefix = "EXTERNAL_"


class LoggingConfig(BaseSettings):
    """Logging configuration with structured logging support."""
    
    level: Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"] = Field(
        default="INFO",
        description="Logging level"
    )
    format: str = Field(
        default="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        description="Log message format"
    )
    file_max_size: int = Field(
        default=10485760,  # 10MB
        ge=1048576,  # 1MB minimum
        description="Maximum log file size in bytes"
    )
    file_backup_count: int = Field(
        default=5,
        ge=1,
        le=50,
        description="Number of backup log files to keep"
    )
    structured_logging: bool = Field(
        default=False,
        description="Enable structured JSON logging"
    )
    
    # APM Configuration
    apm_enabled: bool = Field(
        default=False,
        description="Enable Application Performance Monitoring"
    )
    apm_service_name: str = Field(
        default="drone-survey-system",
        description="APM service name"
    )
    apm_secret_token: Optional[SecretStr] = Field(
        default=None,
        description="APM secret token"
    )
    apm_server_url: Optional[HttpUrl] = Field(
        default=None,
        description="APM server URL"
    )
    
    class Config:
        env_prefix = "LOG_"


class FeatureFlagsConfig(BaseSettings):
    """Feature flags for enabling/disabling functionality."""
    
    # Core Features
    real_time_updates: bool = Field(
        default=True,
        description="Enable real-time WebSocket updates"
    )
    ai_optimization: bool = Field(
        default=True,
        description="Enable AI-powered optimization"
    )
    three_d_visualization: bool = Field(
        default=True,
        description="Enable 3D visualization features",
        alias="3d_visualization_enabled"
    )
    weather_integration: bool = Field(
        default=True,
        description="Enable weather data integration"
    )
    predictive_analytics: bool = Field(
        default=True,
        description="Enable predictive analytics"
    )
    
    # Enterprise Features
    multi_tenant: bool = Field(
        default=False,
        description="Enable multi-tenant support"
    )
    audit_logging: bool = Field(
        default=True,
        description="Enable audit trail logging"
    )
    advanced_security: bool = Field(
        default=False,
        description="Enable advanced security features"
    )
    compliance_reporting: bool = Field(
        default=False,
        description="Enable compliance reporting"
    )
    
    # Experimental Features
    machine_learning_models: bool = Field(
        default=True,
        description="Enable ML model predictions"
    )
    autonomous_mission_planning: bool = Field(
        default=False,
        description="Enable autonomous mission planning"
    )
    swarm_intelligence: bool = Field(
        default=False,
        description="Enable swarm intelligence features"
    )
    
    class Config:
        env_prefix = "FEATURE_"


class MissionConfig(BaseSettings):
    """Mission and drone operational configuration."""
    
    # Altitude Limits
    default_altitude_m: float = Field(
        default=100.0,
        ge=0.0,
        description="Default mission altitude in meters"
    )
    min_altitude_m: float = Field(
        default=30.0,
        ge=0.0,
        description="Minimum allowed altitude in meters"
    )
    max_altitude_m: float = Field(
        default=400.0,
        ge=1.0,
        description="Maximum allowed altitude in meters"
    )
    
    # Mission Parameters
    default_overlap_percentage: float = Field(
        default=60.0,
        ge=0.0,
        le=100.0,
        description="Default image overlap percentage"
    )
    max_mission_duration_hours: int = Field(
        default=8,
        ge=1,
        le=24,
        description="Maximum mission duration in hours"
    )
    max_concurrent_missions: int = Field(
        default=10,
        ge=1,
        le=100,
        description="Maximum concurrent missions"
    )
    
    # Drone Configuration
    battery_low_threshold: float = Field(
        default=20.0,
        ge=0.0,
        le=100.0,
        description="Battery low warning threshold percentage"
    )
    battery_critical_threshold: float = Field(
        default=10.0,
        ge=0.0,
        le=100.0,
        description="Battery critical warning threshold percentage"
    )
    max_flight_time_minutes: int = Field(
        default=25,
        ge=1,
        le=120,
        description="Maximum flight time per mission in minutes"
    )
    
    # Update Intervals
    drone_status_update_interval: int = Field(
        default=5,
        ge=1,
        le=60,
        description="Drone status update interval in seconds"
    )
    mission_progress_update_interval: int = Field(
        default=3,
        ge=1,
        le=30,
        description="Mission progress update interval in seconds"
    )
    fleet_summary_update_interval: int = Field(
        default=10,
        ge=5,
        le=300,
        description="Fleet summary update interval in seconds"
    )
    
    @validator('max_altitude_m')
    def validate_altitude_range(cls, v, values):
        """Ensure max altitude is greater than min altitude."""
        min_alt = values.get('min_altitude_m', 0)
        if v <= min_alt:
            raise ValueError(f"max_altitude_m ({v}) must be greater than min_altitude_m ({min_alt})")
        return v
    
    @validator('battery_critical_threshold')
    def validate_battery_thresholds(cls, v, values):
        """Ensure critical threshold is less than low threshold."""
        low_threshold = values.get('battery_low_threshold', 100)
        if v >= low_threshold:
            raise ValueError(f"battery_critical_threshold ({v}) must be less than battery_low_threshold ({low_threshold})")
        return v
    
    class Config:
        env_prefix = "MISSION_"


class DroneSurveyConfig(BaseSettings):
    """Main configuration class combining all configuration sections."""
    
    # Environment
    environment: Literal["development", "staging", "production", "docker"] = Field(
        default="development",
        description="Application environment"
    )
    debug: bool = Field(
        default=False,
        description="Enable debug mode"
    )
    testing: bool = Field(
        default=False,
        description="Enable testing mode"
    )
    
    # Application Core
    host: str = Field(
        default="localhost",
        description="Application host"
    )
    port: int = Field(
        default=5000,
        ge=1024,
        le=65535,
        description="Application port"
    )
    
    # Configuration Sections
    database: DatabaseConfig = DatabaseConfig()
    security: SecurityConfig = SecurityConfig()
    cache: CacheConfig = CacheConfig()
    external_services: ExternalServicesConfig = ExternalServicesConfig()
    logging: LoggingConfig = LoggingConfig()
    features: FeatureFlagsConfig = FeatureFlagsConfig()
    mission: MissionConfig = MissionConfig()
    
    # CORS Configuration
    cors_origins: List[str] = Field(
        default=["*"],
        description="CORS allowed origins"
    )
    
    @validator('cors_origins', pre=True)
    def parse_cors_origins(cls, v):
        """Parse CORS origins from string or list."""
        if isinstance(v, str):
            return [origin.strip() for origin in v.split(',') if origin.strip()]
        return v
    
    @validator('debug')
    def validate_debug_mode(cls, v, values):
        """Ensure debug is disabled in production."""
        if v and values.get('environment') == 'production':
            raise ValueError("Debug mode must be disabled in production")
        return v
    
    class Config:
        env_file = [
            '.env.local',
            '.env.development',
            '.env.staging', 
            '.env.production',
            '.env'
        ]
        env_file_encoding = 'utf-8'
        case_sensitive = False
        
    def get_database_uri(self) -> str:
        """Get the formatted database URI."""
        return str(self.database.url)
    
    def is_production(self) -> bool:
        """Check if running in production environment."""
        return self.environment == "production"
    
    def is_development(self) -> bool:
        """Check if running in development environment."""
        return self.environment == "development"
    
    def get_log_level(self) -> str:
        """Get the logging level."""
        return self.logging.level
    
    def validate_production_settings(self) -> List[str]:
        """Validate critical production settings and return warnings."""
        warnings = []
        
        if self.is_production():
            # Check secret keys
            if self.security.secret_key.get_secret_value() == "dev-secret-key-change-in-production":
                warnings.append("Production secret key must be changed from default")
            
            # Check database configuration
            if "sqlite" in str(self.database.url):
                warnings.append("SQLite database not recommended for production")
            
            # Check security settings
            if not self.security.csrf_enabled:
                warnings.append("CSRF protection should be enabled in production")
            
            if not self.security.session_cookie_secure:
                warnings.append("Secure cookies should be enabled in production")
        
        return warnings


# Global configuration instance
def get_config() -> DroneSurveyConfig:
    """Get the application configuration instance."""
    return DroneSurveyConfig()


# Configuration validation
def validate_config(config: DroneSurveyConfig) -> Dict[str, Any]:
    """Validate configuration and return validation results."""
    results = {
        "valid": True,
        "warnings": [],
        "errors": []
    }
    
    try:
        # Validate production settings
        if config.is_production():
            warnings = config.validate_production_settings()
            results["warnings"].extend(warnings)
        
        # Additional validation logic can be added here
        
    except Exception as e:
        results["valid"] = False
        results["errors"].append(str(e))
    
    return results
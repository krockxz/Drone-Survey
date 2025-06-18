"""
Base Service Classes for Modular Architecture

This module provides abstract base classes and interfaces for creating
modular, testable, and maintainable services throughout the application.

Author: FlytBase Assignment - Enterprise Edition  
Created: 2024
"""

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional, TypeVar, Generic, Union
from dataclasses import dataclass
from enum import Enum
import logging
from datetime import datetime

from .config_manager import get_config


T = TypeVar('T')


class ServiceResult(Generic[T]):
    """Standard service operation result with success/error handling."""
    
    def __init__(
        self,
        success: bool,
        data: Optional[T] = None,
        error: Optional[str] = None,
        error_code: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ):
        self.success = success
        self.data = data
        self.error = error
        self.error_code = error_code
        self.metadata = metadata or {}
        self.timestamp = datetime.utcnow()
    
    @classmethod
    def success_result(cls, data: T, metadata: Optional[Dict[str, Any]] = None) -> 'ServiceResult[T]':
        """Create a successful result."""
        return cls(success=True, data=data, metadata=metadata)
    
    @classmethod
    def error_result(
        cls, 
        error: str, 
        error_code: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> 'ServiceResult[T]':
        """Create an error result."""
        return cls(success=False, error=error, error_code=error_code, metadata=metadata)
    
    def __bool__(self) -> bool:
        """Allow boolean evaluation of result."""
        return self.success


class LogLevel(Enum):
    """Logging levels for service operations."""
    DEBUG = "DEBUG"
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"


@dataclass
class ServiceMetrics:
    """Service performance and operation metrics."""
    operation_count: int = 0
    success_count: int = 0
    error_count: int = 0
    avg_response_time: float = 0.0
    last_operation_time: Optional[datetime] = None


class BaseService(ABC):
    """
    Abstract base class for all services in the application.
    
    Provides common functionality including:
    - Logging and monitoring
    - Configuration access
    - Error handling patterns
    - Metrics collection
    - Health checking
    """
    
    def __init__(self, name: Optional[str] = None):
        """Initialize base service."""
        self.name = name or self.__class__.__name__
        self.logger = logging.getLogger(f"services.{self.name}")
        self.config = get_config()
        self.metrics = ServiceMetrics()
        self._initialized = False
        
        # Initialize the service
        self.initialize()
    
    def initialize(self) -> None:
        """Initialize service-specific resources."""
        self.logger.info(f"Initializing {self.name} service")
        self._initialized = True
    
    def is_initialized(self) -> bool:
        """Check if service is properly initialized."""
        return self._initialized
    
    def log(self, level: LogLevel, message: str, **kwargs) -> None:
        """Log message with service context."""
        log_method = getattr(self.logger, level.value.lower())
        log_method(f"[{self.name}] {message}", extra=kwargs)
    
    def update_metrics(self, success: bool, response_time: float) -> None:
        """Update service metrics."""
        self.metrics.operation_count += 1
        if success:
            self.metrics.success_count += 1
        else:
            self.metrics.error_count += 1
        
        # Update average response time
        if self.metrics.operation_count == 1:
            self.metrics.avg_response_time = response_time
        else:
            self.metrics.avg_response_time = (
                (self.metrics.avg_response_time * (self.metrics.operation_count - 1) + response_time) /
                self.metrics.operation_count
            )
        
        self.metrics.last_operation_time = datetime.utcnow()
    
    @abstractmethod
    def health_check(self) -> ServiceResult[Dict[str, Any]]:
        """Perform health check and return status."""
        pass
    
    def get_metrics(self) -> ServiceResult[ServiceMetrics]:
        """Get service metrics."""
        return ServiceResult.success_result(self.metrics)
    
    def is_feature_enabled(self, feature_name: str) -> bool:
        """Check if a feature flag is enabled."""
        return self.config.features.__dict__.get(feature_name, False)


class DatabaseService(BaseService):
    """Base class for services that interact with the database."""
    
    def __init__(self, name: Optional[str] = None):
        """Initialize database service."""
        super().__init__(name)
        self.db = None  # Will be injected by application factory
    
    def set_database(self, db):
        """Set database instance (dependency injection)."""
        self.db = db
        self.log(LogLevel.INFO, "Database instance configured")
    
    def health_check(self) -> ServiceResult[Dict[str, Any]]:
        """Check database connectivity."""
        try:
            if self.db is None:
                return ServiceResult.error_result("Database not configured")
            
            # Simple query to check connectivity
            result = self.db.engine.execute("SELECT 1").scalar()
            
            return ServiceResult.success_result({
                "status": "healthy",
                "database_connected": True,
                "timestamp": datetime.utcnow().isoformat()
            })
        except Exception as e:
            self.log(LogLevel.ERROR, f"Database health check failed: {e}")
            return ServiceResult.error_result(f"Database health check failed: {e}")


class ExternalServiceBase(BaseService):
    """Base class for services that interact with external APIs."""
    
    def __init__(self, name: Optional[str] = None, timeout: int = 30):
        """Initialize external service."""
        super().__init__(name)
        self.timeout = timeout
        self.base_url: Optional[str] = None
        self.api_key: Optional[str] = None
    
    def configure_service(self, base_url: str, api_key: Optional[str] = None) -> None:
        """Configure external service connection."""
        self.base_url = base_url
        self.api_key = api_key
        self.log(LogLevel.INFO, f"Configured external service: {base_url}")
    
    def health_check(self) -> ServiceResult[Dict[str, Any]]:
        """Check external service connectivity."""
        if not self.base_url:
            return ServiceResult.error_result("External service not configured")
        
        try:
            # Implement service-specific health check
            return self._perform_health_check()
        except Exception as e:
            self.log(LogLevel.ERROR, f"External service health check failed: {e}")
            return ServiceResult.error_result(f"Health check failed: {e}")
    
    @abstractmethod
    def _perform_health_check(self) -> ServiceResult[Dict[str, Any]]:
        """Perform service-specific health check."""
        pass


class AIServiceBase(BaseService):
    """Base class for AI and machine learning services."""
    
    def __init__(self, name: Optional[str] = None):
        """Initialize AI service."""
        super().__init__(name)
        self.model_loaded = False
        self.model_version: Optional[str] = None
        self.confidence_threshold = 0.85
    
    def load_model(self, model_path: str) -> ServiceResult[bool]:
        """Load AI model from path."""
        try:
            self._load_model_implementation(model_path)
            self.model_loaded = True
            self.log(LogLevel.INFO, f"Model loaded successfully from {model_path}")
            return ServiceResult.success_result(True)
        except Exception as e:
            self.log(LogLevel.ERROR, f"Failed to load model: {e}")
            return ServiceResult.error_result(f"Model loading failed: {e}")
    
    @abstractmethod
    def _load_model_implementation(self, model_path: str) -> None:
        """Implement model loading logic."""
        pass
    
    def predict(self, input_data: Any) -> ServiceResult[Dict[str, Any]]:
        """Make prediction using loaded model."""
        if not self.model_loaded:
            return ServiceResult.error_result("Model not loaded")
        
        try:
            prediction = self._predict_implementation(input_data)
            
            # Check confidence threshold
            confidence = prediction.get('confidence', 0.0)
            if confidence < self.confidence_threshold:
                self.log(LogLevel.WARNING, f"Low confidence prediction: {confidence}")
            
            return ServiceResult.success_result(prediction)
        except Exception as e:
            self.log(LogLevel.ERROR, f"Prediction failed: {e}")
            return ServiceResult.error_result(f"Prediction failed: {e}")
    
    @abstractmethod
    def _predict_implementation(self, input_data: Any) -> Dict[str, Any]:
        """Implement prediction logic."""
        pass
    
    def health_check(self) -> ServiceResult[Dict[str, Any]]:
        """Check AI service health."""
        return ServiceResult.success_result({
            "status": "healthy" if self.model_loaded else "degraded",
            "model_loaded": self.model_loaded,
            "model_version": self.model_version,
            "confidence_threshold": self.confidence_threshold,
            "timestamp": datetime.utcnow().isoformat()
        })


class CacheServiceBase(BaseService):
    """Base class for caching services."""
    
    def __init__(self, name: Optional[str] = None):
        """Initialize cache service."""
        super().__init__(name)
        self.cache_backend = None
    
    def get(self, key: str) -> ServiceResult[Any]:
        """Get value from cache."""
        try:
            value = self._get_implementation(key)
            return ServiceResult.success_result(value)
        except Exception as e:
            self.log(LogLevel.ERROR, f"Cache get failed for key {key}: {e}")
            return ServiceResult.error_result(f"Cache get failed: {e}")
    
    def set(self, key: str, value: Any, timeout: Optional[int] = None) -> ServiceResult[bool]:
        """Set value in cache."""
        try:
            result = self._set_implementation(key, value, timeout)
            return ServiceResult.success_result(result)
        except Exception as e:
            self.log(LogLevel.ERROR, f"Cache set failed for key {key}: {e}")
            return ServiceResult.error_result(f"Cache set failed: {e}")
    
    def delete(self, key: str) -> ServiceResult[bool]:
        """Delete value from cache."""
        try:
            result = self._delete_implementation(key)
            return ServiceResult.success_result(result)
        except Exception as e:
            self.log(LogLevel.ERROR, f"Cache delete failed for key {key}: {e}")
            return ServiceResult.error_result(f"Cache delete failed: {e}")
    
    @abstractmethod
    def _get_implementation(self, key: str) -> Any:
        """Implement cache get logic."""
        pass
    
    @abstractmethod
    def _set_implementation(self, key: str, value: Any, timeout: Optional[int] = None) -> bool:
        """Implement cache set logic."""
        pass
    
    @abstractmethod
    def _delete_implementation(self, key: str) -> bool:
        """Implement cache delete logic."""
        pass
    
    def health_check(self) -> ServiceResult[Dict[str, Any]]:
        """Check cache service health."""
        try:
            # Test cache with a simple operation
            test_key = f"health_check_{datetime.utcnow().timestamp()}"
            self.set(test_key, "test_value", timeout=60)
            value = self.get(test_key)
            self.delete(test_key)
            
            return ServiceResult.success_result({
                "status": "healthy",
                "cache_operational": True,
                "timestamp": datetime.utcnow().isoformat()
            })
        except Exception as e:
            return ServiceResult.error_result(f"Cache health check failed: {e}")


class ServiceRegistry:
    """Registry for managing service instances and dependencies."""
    
    def __init__(self):
        """Initialize service registry."""
        self._services: Dict[str, BaseService] = {}
        self._dependencies: Dict[str, List[str]] = {}
    
    def register_service(self, service: BaseService, dependencies: Optional[List[str]] = None) -> None:
        """Register a service with optional dependencies."""
        service_name = service.name
        self._services[service_name] = service
        self._dependencies[service_name] = dependencies or []
        
        logging.info(f"Registered service: {service_name}")
    
    def get_service(self, service_name: str) -> Optional[BaseService]:
        """Get service by name."""
        return self._services.get(service_name)
    
    def get_all_services(self) -> Dict[str, BaseService]:
        """Get all registered services."""
        return self._services.copy()
    
    def health_check_all(self) -> Dict[str, ServiceResult]:
        """Perform health check on all services."""
        results = {}
        for name, service in self._services.items():
            results[name] = service.health_check()
        return results
    
    def initialize_services(self) -> List[str]:
        """Initialize all services in dependency order."""
        initialized = []
        
        # Simple dependency resolution (topological sort would be better for complex deps)
        for name, service in self._services.items():
            if not service.is_initialized():
                service.initialize()
            initialized.append(name)
        
        return initialized


# Global service registry
_service_registry: Optional[ServiceRegistry] = None


def get_service_registry() -> ServiceRegistry:
    """Get the global service registry."""
    global _service_registry
    if _service_registry is None:
        _service_registry = ServiceRegistry()
    return _service_registry
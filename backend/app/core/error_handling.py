"""
Enterprise Error Handling and Exception Management

Comprehensive error handling system with structured exceptions,
logging, monitoring integration, and graceful degradation patterns.

Author: FlytBase Assignment - Enterprise Edition
Created: 2024
"""

import traceback
import sys
from typing import Any, Dict, Optional, Type, Union, List
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
import logging
import uuid

from flask import Flask, request, jsonify, g
from werkzeug.exceptions import HTTPException


class ErrorSeverity(Enum):
    """Error severity levels for classification and alerting."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class ErrorCategory(Enum):
    """Error categories for better organization and handling."""
    VALIDATION = "validation"
    AUTHENTICATION = "authentication"
    AUTHORIZATION = "authorization"
    BUSINESS_LOGIC = "business_logic"
    EXTERNAL_SERVICE = "external_service"
    DATABASE = "database"
    SYSTEM = "system"
    NETWORK = "network"
    AI_MODEL = "ai_model"


@dataclass
class ErrorContext:
    """Context information for errors."""
    user_id: Optional[str] = None
    request_id: Optional[str] = None
    endpoint: Optional[str] = None
    method: Optional[str] = None
    ip_address: Optional[str] = None
    user_agent: Optional[str] = None
    additional_data: Dict[str, Any] = field(default_factory=dict)


class BaseApplicationError(Exception):
    """Base application error with rich context and metadata."""
    
    def __init__(
        self,
        message: str,
        error_code: Optional[str] = None,
        category: ErrorCategory = ErrorCategory.SYSTEM,
        severity: ErrorSeverity = ErrorSeverity.MEDIUM,
        context: Optional[ErrorContext] = None,
        cause: Optional[Exception] = None,
        user_message: Optional[str] = None,
        retry_after: Optional[int] = None,
        metadata: Optional[Dict[str, Any]] = None
    ):
        super().__init__(message)
        self.message = message
        self.error_code = error_code or self.__class__.__name__
        self.category = category
        self.severity = severity
        self.context = context or ErrorContext()
        self.cause = cause
        self.user_message = user_message or "An error occurred while processing your request"
        self.retry_after = retry_after
        self.metadata = metadata or {}
        self.timestamp = datetime.utcnow()
        self.error_id = str(uuid.uuid4())
    
    def to_dict(self, include_sensitive: bool = False) -> Dict[str, Any]:
        """Convert error to dictionary for logging/API responses."""
        error_dict = {
            "error_id": self.error_id,
            "error_code": self.error_code,
            "message": self.user_message,
            "category": self.category.value,
            "severity": self.severity.value,
            "timestamp": self.timestamp.isoformat(),
            "metadata": self.metadata
        }
        
        if include_sensitive:
            error_dict.update({
                "detailed_message": self.message,
                "context": {
                    "user_id": self.context.user_id,
                    "request_id": self.context.request_id,
                    "endpoint": self.context.endpoint,
                    "method": self.context.method,
                    "ip_address": self.context.ip_address,
                    "additional_data": self.context.additional_data
                },
                "cause": str(self.cause) if self.cause else None,
                "traceback": traceback.format_exc() if self.cause else None
            })
        
        if self.retry_after:
            error_dict["retry_after"] = self.retry_after
        
        return error_dict


class ValidationError(BaseApplicationError):
    """Validation errors for input data."""
    
    def __init__(self, message: str, field: Optional[str] = None, **kwargs):
        super().__init__(
            message,
            category=ErrorCategory.VALIDATION,
            severity=ErrorSeverity.LOW,
            **kwargs
        )
        if field:
            self.metadata["field"] = field


class AuthenticationError(BaseApplicationError):
    """Authentication failures."""
    
    def __init__(self, message: str = "Authentication required", **kwargs):
        super().__init__(
            message,
            category=ErrorCategory.AUTHENTICATION,
            severity=ErrorSeverity.MEDIUM,
            user_message="Authentication required",
            **kwargs
        )


class AuthorizationError(BaseApplicationError):
    """Authorization failures."""
    
    def __init__(self, message: str = "Insufficient permissions", **kwargs):
        super().__init__(
            message,
            category=ErrorCategory.AUTHORIZATION,
            severity=ErrorSeverity.MEDIUM,
            user_message="You don't have permission to access this resource",
            **kwargs
        )


class BusinessLogicError(BaseApplicationError):
    """Business logic violations."""
    
    def __init__(self, message: str, **kwargs):
        super().__init__(
            message,
            category=ErrorCategory.BUSINESS_LOGIC,
            severity=ErrorSeverity.MEDIUM,
            **kwargs
        )


class ExternalServiceError(BaseApplicationError):
    """External service integration errors."""
    
    def __init__(self, message: str, service_name: str, **kwargs):
        super().__init__(
            message,
            category=ErrorCategory.EXTERNAL_SERVICE,
            severity=ErrorSeverity.HIGH,
            user_message="External service temporarily unavailable",
            retry_after=300,  # 5 minutes
            **kwargs
        )
        self.metadata["service_name"] = service_name


class DatabaseError(BaseApplicationError):
    """Database operation errors."""
    
    def __init__(self, message: str, operation: Optional[str] = None, **kwargs):
        super().__init__(
            message,
            category=ErrorCategory.DATABASE,
            severity=ErrorSeverity.HIGH,
            user_message="Database operation failed",
            **kwargs
        )
        if operation:
            self.metadata["operation"] = operation


class AIModelError(BaseApplicationError):
    """AI/ML model errors."""
    
    def __init__(self, message: str, model_name: Optional[str] = None, **kwargs):
        super().__init__(
            message,
            category=ErrorCategory.AI_MODEL,
            severity=ErrorSeverity.HIGH,
            user_message="AI service temporarily unavailable",
            retry_after=60,
            **kwargs
        )
        if model_name:
            self.metadata["model_name"] = model_name


class SystemError(BaseApplicationError):
    """System-level errors."""
    
    def __init__(self, message: str, **kwargs):
        super().__init__(
            message,
            category=ErrorCategory.SYSTEM,
            severity=ErrorSeverity.CRITICAL,
            user_message="System error occurred",
            **kwargs
        )


class ErrorHandler:
    """Central error handler with logging, monitoring, and alerting."""
    
    def __init__(self, app: Optional[Flask] = None):
        """Initialize error handler."""
        self.app = app
        self.logger = logging.getLogger("error_handler")
        self.error_count = 0
        self.last_errors: List[BaseApplicationError] = []
        
        if app:
            self.init_app(app)
    
    def init_app(self, app: Flask) -> None:
        """Initialize error handler with Flask app."""
        self.app = app
        
        # Register error handlers
        app.errorhandler(BaseApplicationError)(self.handle_application_error)
        app.errorhandler(HTTPException)(self.handle_http_error)
        app.errorhandler(Exception)(self.handle_generic_error)
        
        # Register request context processor
        app.before_request(self.before_request)
    
    def before_request(self) -> None:
        """Set up error context for each request."""
        g.request_id = str(uuid.uuid4())
        g.start_time = datetime.utcnow()
    
    def create_error_context(self) -> ErrorContext:
        """Create error context from current request."""
        return ErrorContext(
            user_id=getattr(g, 'user_id', None),
            request_id=getattr(g, 'request_id', None),
            endpoint=request.endpoint,
            method=request.method,
            ip_address=request.remote_addr,
            user_agent=request.headers.get('User-Agent'),
            additional_data={
                "url": request.url,
                "args": dict(request.args),
                "form": dict(request.form) if request.form else None,
            }
        )
    
    def handle_application_error(self, error: BaseApplicationError):
        """Handle application-specific errors."""
        # Add request context if not present
        if not error.context or not error.context.request_id:
            error.context = self.create_error_context()
        
        # Log error
        self.log_error(error)
        
        # Update metrics
        self.update_error_metrics(error)
        
        # Send to monitoring service
        self.send_to_monitoring(error)
        
        # Create API response
        status_code = self.get_http_status_code(error)
        response_data = error.to_dict(include_sensitive=False)
        
        return jsonify(response_data), status_code
    
    def handle_http_error(self, error: HTTPException):
        """Handle HTTP errors."""
        app_error = BaseApplicationError(
            message=error.description or "HTTP error occurred",
            error_code=f"HTTP_{error.code}",
            category=ErrorCategory.SYSTEM,
            severity=ErrorSeverity.MEDIUM,
            context=self.create_error_context(),
            user_message=error.description or f"HTTP {error.code} error"
        )
        
        return self.handle_application_error(app_error)
    
    def handle_generic_error(self, error: Exception):
        """Handle unexpected errors."""
        app_error = SystemError(
            message=f"Unexpected error: {str(error)}",
            error_code="UNEXPECTED_ERROR",
            context=self.create_error_context(),
            cause=error
        )
        
        return self.handle_application_error(app_error)
    
    def log_error(self, error: BaseApplicationError) -> None:
        """Log error with appropriate level and structure."""
        log_data = error.to_dict(include_sensitive=True)
        
        # Determine log level based on severity
        if error.severity == ErrorSeverity.CRITICAL:
            self.logger.critical("Critical error occurred", extra=log_data)
        elif error.severity == ErrorSeverity.HIGH:
            self.logger.error("High severity error", extra=log_data)
        elif error.severity == ErrorSeverity.MEDIUM:
            self.logger.warning("Medium severity error", extra=log_data)
        else:
            self.logger.info("Low severity error", extra=log_data)
    
    def update_error_metrics(self, error: BaseApplicationError) -> None:
        """Update error metrics and tracking."""
        self.error_count += 1
        self.last_errors.append(error)
        
        # Keep only last 100 errors
        if len(self.last_errors) > 100:
            self.last_errors = self.last_errors[-100:]
    
    def send_to_monitoring(self, error: BaseApplicationError) -> None:
        """Send error to monitoring/alerting service."""
        try:
            # Integration with monitoring services (Sentry, New Relic, etc.)
            # This would be implemented based on the chosen monitoring solution
            pass
        except Exception as e:
            self.logger.error(f"Failed to send error to monitoring: {e}")
    
    def get_http_status_code(self, error: BaseApplicationError) -> int:
        """Determine HTTP status code for error."""
        status_mapping = {
            ErrorCategory.VALIDATION: 400,
            ErrorCategory.AUTHENTICATION: 401,
            ErrorCategory.AUTHORIZATION: 403,
            ErrorCategory.BUSINESS_LOGIC: 400,
            ErrorCategory.EXTERNAL_SERVICE: 502,
            ErrorCategory.DATABASE: 500,
            ErrorCategory.AI_MODEL: 503,
            ErrorCategory.SYSTEM: 500,
            ErrorCategory.NETWORK: 502,
        }
        
        return status_mapping.get(error.category, 500)
    
    def get_error_statistics(self) -> Dict[str, Any]:
        """Get error statistics for monitoring."""
        if not self.last_errors:
            return {"total_errors": 0}
        
        categories = {}
        severities = {}
        
        for error in self.last_errors:
            categories[error.category.value] = categories.get(error.category.value, 0) + 1
            severities[error.severity.value] = severities.get(error.severity.value, 0) + 1
        
        return {
            "total_errors": self.error_count,
            "recent_errors": len(self.last_errors),
            "categories": categories,
            "severities": severities,
            "last_error_time": self.last_errors[-1].timestamp.isoformat() if self.last_errors else None
        }


class CircuitBreaker:
    """Circuit breaker pattern for external service calls."""
    
    def __init__(
        self,
        failure_threshold: int = 5,
        recovery_timeout: int = 60,
        expected_exception: Type[Exception] = Exception
    ):
        """Initialize circuit breaker."""
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.expected_exception = expected_exception
        
        self.failure_count = 0
        self.last_failure_time = None
        self.state = "CLOSED"  # CLOSED, OPEN, HALF_OPEN
    
    def __call__(self, func):
        """Decorator to apply circuit breaker to function."""
        def wrapper(*args, **kwargs):
            if self.state == "OPEN":
                if self._should_attempt_reset():
                    self.state = "HALF_OPEN"
                else:
                    raise ExternalServiceError(
                        "Service unavailable (circuit breaker open)",
                        service_name=func.__name__,
                        retry_after=self.recovery_timeout
                    )
            
            try:
                result = func(*args, **kwargs)
                self._on_success()
                return result
            except self.expected_exception as e:
                self._on_failure()
                raise
        
        return wrapper
    
    def _should_attempt_reset(self) -> bool:
        """Check if circuit breaker should attempt reset."""
        return (
            self.last_failure_time and
            (datetime.utcnow().timestamp() - self.last_failure_time) >= self.recovery_timeout
        )
    
    def _on_success(self) -> None:
        """Handle successful call."""
        self.failure_count = 0
        self.state = "CLOSED"
    
    def _on_failure(self) -> None:
        """Handle failed call."""
        self.failure_count += 1
        self.last_failure_time = datetime.utcnow().timestamp()
        
        if self.failure_count >= self.failure_threshold:
            self.state = "OPEN"


# Global error handler instance
_error_handler: Optional[ErrorHandler] = None


def get_error_handler() -> ErrorHandler:
    """Get global error handler instance."""
    global _error_handler
    if _error_handler is None:
        _error_handler = ErrorHandler()
    return _error_handler


def init_error_handling(app: Flask) -> ErrorHandler:
    """Initialize error handling for Flask app."""
    error_handler = get_error_handler()
    error_handler.init_app(app)
    return error_handler
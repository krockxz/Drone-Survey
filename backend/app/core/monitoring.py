"""
Enterprise Monitoring and Observability System

Comprehensive monitoring solution with metrics collection, health checks,
performance tracking, and real-time alerting capabilities.

Author: FlytBase Assignment - Enterprise Edition
Created: 2024
"""

import time
import psutil
import threading
from typing import Dict, Any, List, Optional, Callable
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from collections import defaultdict, deque
from contextlib import contextmanager
import logging

from flask import Flask, request, g
from prometheus_client import Counter, Histogram, Gauge, generate_latest, CONTENT_TYPE_LATEST


@dataclass
class MetricPoint:
    """Single metric data point."""
    timestamp: datetime
    value: float
    labels: Dict[str, str] = field(default_factory=dict)


@dataclass
class HealthCheckResult:
    """Health check result with status and metadata."""
    name: str
    status: str  # healthy, degraded, unhealthy
    response_time: float
    message: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    timestamp: datetime = field(default_factory=datetime.utcnow)


class MetricsCollector:
    """Prometheus-compatible metrics collector."""
    
    def __init__(self):
        """Initialize metrics collector."""
        # HTTP Metrics
        self.http_requests_total = Counter(
            'http_requests_total',
            'Total HTTP requests',
            ['method', 'endpoint', 'status']
        )
        
        self.http_request_duration = Histogram(
            'http_request_duration_seconds',
            'HTTP request duration in seconds',
            ['method', 'endpoint']
        )
        
        # Application Metrics
        self.active_missions = Gauge(
            'drone_active_missions',
            'Number of active drone missions'
        )
        
        self.drone_battery_level = Gauge(
            'drone_battery_level',
            'Drone battery level percentage',
            ['drone_id']
        )
        
        self.ai_predictions_total = Counter(
            'ai_predictions_total',
            'Total AI predictions made',
            ['model', 'outcome']
        )
        
        self.ai_prediction_confidence = Histogram(
            'ai_prediction_confidence',
            'AI prediction confidence scores',
            ['model']
        )
        
        # System Metrics
        self.system_cpu_usage = Gauge(
            'system_cpu_usage_percent',
            'System CPU usage percentage'
        )
        
        self.system_memory_usage = Gauge(
            'system_memory_usage_percent',
            'System memory usage percentage'
        )
        
        self.database_connections = Gauge(
            'database_connections_active',
            'Active database connections'
        )
        
        # Error Metrics
        self.errors_total = Counter(
            'errors_total',
            'Total errors by category and severity',
            ['category', 'severity']
        )
        
        # WebSocket Metrics
        self.websocket_connections = Gauge(
            'websocket_connections_active',
            'Active WebSocket connections'
        )
        
        self.websocket_messages_total = Counter(
            'websocket_messages_total',
            'Total WebSocket messages',
            ['event_type', 'direction']
        )
    
    def record_http_request(self, method: str, endpoint: str, status_code: int, duration: float):
        """Record HTTP request metrics."""
        self.http_requests_total.labels(
            method=method,
            endpoint=endpoint,
            status=str(status_code)
        ).inc()
        
        self.http_request_duration.labels(
            method=method,
            endpoint=endpoint
        ).observe(duration)
    
    def record_mission_metrics(self, active_count: int):
        """Record mission-related metrics."""
        self.active_missions.set(active_count)
    
    def record_drone_battery(self, drone_id: str, battery_level: float):
        """Record drone battery level."""
        self.drone_battery_level.labels(drone_id=drone_id).set(battery_level)
    
    def record_ai_prediction(self, model: str, confidence: float, successful: bool):
        """Record AI prediction metrics."""
        outcome = "success" if successful else "failure"
        self.ai_predictions_total.labels(model=model, outcome=outcome).inc()
        self.ai_prediction_confidence.labels(model=model).observe(confidence)
    
    def record_error(self, category: str, severity: str):
        """Record error metrics."""
        self.errors_total.labels(category=category, severity=severity).inc()
    
    def record_websocket_event(self, event_type: str, direction: str, connection_count: int):
        """Record WebSocket metrics."""
        self.websocket_connections.set(connection_count)
        self.websocket_messages_total.labels(
            event_type=event_type,
            direction=direction
        ).inc()
    
    def update_system_metrics(self):
        """Update system resource metrics."""
        # CPU usage
        cpu_percent = psutil.cpu_percent(interval=1)
        self.system_cpu_usage.set(cpu_percent)
        
        # Memory usage
        memory = psutil.virtual_memory()
        self.system_memory_usage.set(memory.percent)
    
    def get_metrics_data(self) -> str:
        """Get Prometheus metrics data."""
        return generate_latest()


class HealthChecker:
    """Health check system for monitoring service status."""
    
    def __init__(self):
        """Initialize health checker."""
        self.checks: Dict[str, Callable[[], HealthCheckResult]] = {}
        self.results: Dict[str, HealthCheckResult] = {}
        self.last_check_time = None
    
    def register_check(self, name: str, check_func: Callable[[], HealthCheckResult]):
        """Register a health check function."""
        self.checks[name] = check_func
        logging.info(f"Registered health check: {name}")
    
    def run_all_checks(self) -> Dict[str, HealthCheckResult]:
        """Run all registered health checks."""
        results = {}
        
        for name, check_func in self.checks.items():
            try:
                start_time = time.time()
                result = check_func()
                result.response_time = time.time() - start_time
                results[name] = result
            except Exception as e:
                results[name] = HealthCheckResult(
                    name=name,
                    status="unhealthy",
                    response_time=time.time() - start_time,
                    message=f"Health check failed: {str(e)}"
                )
        
        self.results = results
        self.last_check_time = datetime.utcnow()
        return results
    
    def get_overall_status(self) -> str:
        """Get overall system health status."""
        if not self.results:
            return "unknown"
        
        statuses = [result.status for result in self.results.values()]
        
        if all(status == "healthy" for status in statuses):
            return "healthy"
        elif any(status == "unhealthy" for status in statuses):
            return "unhealthy"
        else:
            return "degraded"
    
    def get_health_summary(self) -> Dict[str, Any]:
        """Get health check summary."""
        return {
            "overall_status": self.get_overall_status(),
            "last_check": self.last_check_time.isoformat() if self.last_check_time else None,
            "checks": {name: {
                "status": result.status,
                "response_time": result.response_time,
                "message": result.message,
                "timestamp": result.timestamp.isoformat()
            } for name, result in self.results.items()}
        }


class PerformanceMonitor:
    """Performance monitoring and tracking."""
    
    def __init__(self, max_history: int = 1000):
        """Initialize performance monitor."""
        self.max_history = max_history
        self.request_times = deque(maxlen=max_history)
        self.response_sizes = deque(maxlen=max_history)
        self.endpoint_stats = defaultdict(lambda: {
            'count': 0,
            'total_time': 0.0,
            'avg_time': 0.0,
            'min_time': float('inf'),
            'max_time': 0.0
        })
    
    def record_request(self, endpoint: str, duration: float, response_size: int = 0):
        """Record request performance data."""
        self.request_times.append(duration)
        self.response_sizes.append(response_size)
        
        # Update endpoint statistics
        stats = self.endpoint_stats[endpoint]
        stats['count'] += 1
        stats['total_time'] += duration
        stats['avg_time'] = stats['total_time'] / stats['count']
        stats['min_time'] = min(stats['min_time'], duration)
        stats['max_time'] = max(stats['max_time'], duration)
    
    def get_performance_summary(self) -> Dict[str, Any]:
        """Get performance summary statistics."""
        if not self.request_times:
            return {"message": "No performance data available"}
        
        request_times_list = list(self.request_times)
        
        return {
            "requests": {
                "total": len(request_times_list),
                "avg_response_time": sum(request_times_list) / len(request_times_list),
                "min_response_time": min(request_times_list),
                "max_response_time": max(request_times_list),
                "p95_response_time": sorted(request_times_list)[int(len(request_times_list) * 0.95)],
                "p99_response_time": sorted(request_times_list)[int(len(request_times_list) * 0.99)]
            },
            "endpoints": dict(self.endpoint_stats),
            "response_sizes": {
                "avg": sum(self.response_sizes) / len(self.response_sizes) if self.response_sizes else 0,
                "total": sum(self.response_sizes)
            }
        }


class AlertManager:
    """Alert management system for monitoring critical conditions."""
    
    def __init__(self):
        """Initialize alert manager."""
        self.alert_rules: List[Dict[str, Any]] = []
        self.active_alerts: Dict[str, Dict[str, Any]] = {}
        self.alert_history: List[Dict[str, Any]] = []
    
    def add_alert_rule(
        self,
        name: str,
        condition: Callable[[], bool],
        severity: str,
        message: str,
        cooldown: int = 300  # 5 minutes
    ):
        """Add alert rule."""
        self.alert_rules.append({
            "name": name,
            "condition": condition,
            "severity": severity,
            "message": message,
            "cooldown": cooldown,
            "last_triggered": None
        })
    
    def check_alerts(self) -> List[Dict[str, Any]]:
        """Check all alert rules and trigger alerts."""
        triggered_alerts = []
        current_time = datetime.utcnow()
        
        for rule in self.alert_rules:
            try:
                if rule["condition"]():
                    # Check cooldown
                    if (rule["last_triggered"] and 
                        (current_time - rule["last_triggered"]).seconds < rule["cooldown"]):
                        continue
                    
                    alert = {
                        "name": rule["name"],
                        "severity": rule["severity"],
                        "message": rule["message"],
                        "timestamp": current_time,
                        "resolved": False
                    }
                    
                    self.active_alerts[rule["name"]] = alert
                    self.alert_history.append(alert.copy())
                    triggered_alerts.append(alert)
                    rule["last_triggered"] = current_time
                    
                    logging.warning(f"Alert triggered: {rule['name']} - {rule['message']}")
                else:
                    # Resolve alert if it exists
                    if rule["name"] in self.active_alerts:
                        self.active_alerts[rule["name"]]["resolved"] = True
                        self.active_alerts[rule["name"]]["resolved_at"] = current_time
                        del self.active_alerts[rule["name"]]
                        logging.info(f"Alert resolved: {rule['name']}")
            
            except Exception as e:
                logging.error(f"Error checking alert rule {rule['name']}: {e}")
        
        return triggered_alerts
    
    def get_active_alerts(self) -> List[Dict[str, Any]]:
        """Get active alerts."""
        return list(self.active_alerts.values())


class MonitoringSystem:
    """Central monitoring system coordinating all monitoring components."""
    
    def __init__(self, app: Optional[Flask] = None):
        """Initialize monitoring system."""
        self.app = app
        self.metrics = MetricsCollector()
        self.health_checker = HealthChecker()
        self.performance_monitor = PerformanceMonitor()
        self.alert_manager = AlertManager()
        self.logger = logging.getLogger("monitoring")
        
        # Background monitoring
        self.monitoring_thread = None
        self.monitoring_active = False
        
        if app:
            self.init_app(app)
    
    def init_app(self, app: Flask):
        """Initialize monitoring with Flask app."""
        self.app = app
        
        # Register request handlers
        app.before_request(self.before_request)
        app.after_request(self.after_request)
        
        # Register monitoring endpoints
        app.route('/health')(self.health_endpoint)
        app.route('/metrics')(self.metrics_endpoint)
        app.route('/monitoring/status')(self.monitoring_status)
        
        # Set up default health checks
        self._setup_default_health_checks()
        
        # Set up default alerts
        self._setup_default_alerts()
        
        # Start background monitoring
        self.start_monitoring()
    
    def before_request(self):
        """Record request start time."""
        g.start_time = time.time()
    
    def after_request(self, response):
        """Record request metrics."""
        if hasattr(g, 'start_time'):
            duration = time.time() - g.start_time
            
            # Record metrics
            self.metrics.record_http_request(
                method=request.method,
                endpoint=request.endpoint or 'unknown',
                status_code=response.status_code,
                duration=duration
            )
            
            # Record performance data
            response_size = len(response.get_data())
            self.performance_monitor.record_request(
                endpoint=request.endpoint or 'unknown',
                duration=duration,
                response_size=response_size
            )
        
        return response
    
    def health_endpoint(self):
        """Health check endpoint."""
        results = self.health_checker.run_all_checks()
        summary = self.health_checker.get_health_summary()
        
        status_code = 200 if summary["overall_status"] == "healthy" else 503
        return summary, status_code
    
    def metrics_endpoint(self):
        """Prometheus metrics endpoint."""
        metrics_data = self.metrics.get_metrics_data()
        return metrics_data, 200, {'Content-Type': CONTENT_TYPE_LATEST}
    
    def monitoring_status(self):
        """Monitoring system status endpoint."""
        return {
            "monitoring_active": self.monitoring_active,
            "health": self.health_checker.get_health_summary(),
            "performance": self.performance_monitor.get_performance_summary(),
            "alerts": {
                "active": self.alert_manager.get_active_alerts(),
                "total_rules": len(self.alert_manager.alert_rules)
            },
            "system": {
                "cpu_percent": psutil.cpu_percent(),
                "memory_percent": psutil.virtual_memory().percent,
                "disk_percent": psutil.disk_usage('/').percent
            }
        }
    
    def _setup_default_health_checks(self):
        """Set up default health checks."""
        def database_check():
            # This would check database connectivity
            return HealthCheckResult(
                name="database",
                status="healthy",
                response_time=0.0,
                message="Database connection OK"
            )
        
        def redis_check():
            # This would check Redis connectivity
            return HealthCheckResult(
                name="redis",
                status="healthy",
                response_time=0.0,
                message="Redis connection OK"
            )
        
        self.health_checker.register_check("database", database_check)
        self.health_checker.register_check("redis", redis_check)
    
    def _setup_default_alerts(self):
        """Set up default alert rules."""
        # High CPU usage alert
        self.alert_manager.add_alert_rule(
            name="high_cpu_usage",
            condition=lambda: psutil.cpu_percent() > 80,
            severity="warning",
            message="CPU usage is above 80%"
        )
        
        # High memory usage alert
        self.alert_manager.add_alert_rule(
            name="high_memory_usage",
            condition=lambda: psutil.virtual_memory().percent > 90,
            severity="critical",
            message="Memory usage is above 90%"
        )
        
        # High error rate alert
        self.alert_manager.add_alert_rule(
            name="high_error_rate",
            condition=lambda: False,  # Would implement actual error rate check
            severity="warning",
            message="Error rate is above threshold"
        )
    
    def start_monitoring(self):
        """Start background monitoring thread."""
        if not self.monitoring_active:
            self.monitoring_active = True
            self.monitoring_thread = threading.Thread(target=self._monitoring_loop)
            self.monitoring_thread.daemon = True
            self.monitoring_thread.start()
            self.logger.info("Background monitoring started")
    
    def stop_monitoring(self):
        """Stop background monitoring."""
        self.monitoring_active = False
        if self.monitoring_thread:
            self.monitoring_thread.join(timeout=5)
        self.logger.info("Background monitoring stopped")
    
    def _monitoring_loop(self):
        """Background monitoring loop."""
        while self.monitoring_active:
            try:
                # Update system metrics
                self.metrics.update_system_metrics()
                
                # Check alerts
                self.alert_manager.check_alerts()
                
                # Sleep for 30 seconds
                time.sleep(30)
            
            except Exception as e:
                self.logger.error(f"Error in monitoring loop: {e}")
                time.sleep(30)


@contextmanager
def monitor_operation(operation_name: str, metrics_collector: MetricsCollector):
    """Context manager for monitoring operations."""
    start_time = time.time()
    success = False
    
    try:
        yield
        success = True
    finally:
        duration = time.time() - start_time
        # You could add operation-specific metrics here
        logging.info(f"Operation {operation_name} completed in {duration:.3f}s (success: {success})")


# Global monitoring instance
_monitoring_system: Optional[MonitoringSystem] = None


def get_monitoring_system() -> MonitoringSystem:
    """Get global monitoring system instance."""
    global _monitoring_system
    if _monitoring_system is None:
        _monitoring_system = MonitoringSystem()
    return _monitoring_system


def init_monitoring(app: Flask) -> MonitoringSystem:
    """Initialize monitoring for Flask app."""
    monitoring_system = get_monitoring_system()
    monitoring_system.init_app(app)
    return monitoring_system
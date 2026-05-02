"""
Performance monitoring utilities for data capture operations.

Provides timing, metrics collection, and performance alerting for
database operations and simulation data capture.
"""

import time
import psutil
from contextlib import contextmanager
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any
from datetime import datetime, timezone

from hopilot.logging_config import get_logger

logger = get_logger(__name__)


@dataclass
class PerformanceMetrics:
    """Container for performance metrics."""

    operation_name: str
    start_time: float
    end_time: Optional[float] = None
    duration_ms: Optional[float] = None
    memory_usage_mb: Optional[float] = None
    cpu_percent: Optional[float] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    @property
    def duration_seconds(self) -> Optional[float]:
        """Get duration in seconds."""
        return self.duration_ms / 1000 if self.duration_ms else None

    def complete(self) -> None:
        """Mark the operation as complete and calculate metrics."""
        self.end_time = time.time()
        self.duration_ms = (self.end_time - self.start_time) * 1000

        # Collect system metrics
        process = psutil.Process()
        self.memory_usage_mb = process.memory_info().rss / (1024 * 1024)
        self.cpu_percent = process.cpu_percent()

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for logging/storage."""
        return {
            'operation_name': self.operation_name,
            'start_time': datetime.fromtimestamp(self.start_time, tz=timezone.utc).isoformat(),
            'end_time': datetime.fromtimestamp(self.end_time, tz=timezone.utc).isoformat() if self.end_time else None,
            'duration_ms': self.duration_ms,
            'memory_usage_mb': self.memory_usage_mb,
            'cpu_percent': self.cpu_percent,
            'metadata': self.metadata
        }


class PerformanceMonitor:
    """
    Performance monitoring system for data capture operations.

    Tracks timing, memory usage, and CPU metrics for database operations
    and provides alerting for performance degradation.
    """

    def __init__(self, alert_threshold_percent: float = 15.0):
        self.alert_threshold_percent = alert_threshold_percent
        self.baseline_metrics: Dict[str, float] = {}
        self.current_metrics: List[PerformanceMetrics] = []
        self.logger = get_logger(__name__)

    @contextmanager
    def track_operation(self, operation_name: str, **metadata):
        """
        Context manager to track performance of an operation.

        Args:
            operation_name: Name of the operation being tracked
            **metadata: Additional metadata to store with metrics
        """
        metrics = PerformanceMetrics(
            operation_name=operation_name,
            start_time=time.time(),
            metadata=metadata
        )

        try:
            yield metrics
        finally:
            metrics.complete()
            self.current_metrics.append(metrics)
            self._log_metrics(metrics)
            self._check_performance_alert(metrics)

    def _log_metrics(self, metrics: PerformanceMetrics) -> None:
        """Log performance metrics."""
        self.logger.debug(
            f"Performance: {metrics.operation_name} completed in {metrics.duration_ms:.2f}ms, "
            f"Memory: {metrics.memory_usage_mb:.1f}MB, CPU: {metrics.cpu_percent:.1f}%"
        )

    def _check_performance_alert(self, metrics: PerformanceMetrics) -> None:
        """Check if performance has degraded beyond threshold."""
        if metrics.operation_name not in self.baseline_metrics:
            # Establish baseline on first run
            self.baseline_metrics[metrics.operation_name] = metrics.duration_ms
            self.logger.info(f"Established baseline for {metrics.operation_name}: {metrics.duration_ms:.2f}ms")
            return

        baseline = self.baseline_metrics[metrics.operation_name]
        current = metrics.duration_ms
        degradation_percent = ((current - baseline) / baseline) * 100

        if degradation_percent > self.alert_threshold_percent:
            self.logger.warning(
                f"PERFORMANCE ALERT: {metrics.operation_name} degraded by {degradation_percent:.1f}% "
                f"(baseline: {baseline:.2f}ms, current: {current:.2f}ms)"
            )

            # Update baseline to current (adaptive baseline)
            self.baseline_metrics[metrics.operation_name] = current
            self.logger.info(f"Updated baseline for {metrics.operation_name} to {current:.2f}ms")

    def get_recent_metrics(self, operation_name: Optional[str] = None, limit: int = 10) -> List[PerformanceMetrics]:
        """Get recent performance metrics."""
        metrics = self.current_metrics
        if operation_name:
            metrics = [m for m in metrics if m.operation_name == operation_name]
        return metrics[-limit:]

    def get_performance_summary(self) -> Dict[str, Any]:
        """Get performance summary statistics."""
        if not self.current_metrics:
            return {}

        summary = {}
        operations = set(m.operation_name for m in self.current_metrics)

        for op in operations:
            op_metrics = [m for m in self.current_metrics if m.operation_name == op]
            durations = [m.duration_ms for m in op_metrics if m.duration_ms]

            if durations:
                summary[op] = {
                    'count': len(durations),
                    'avg_duration_ms': sum(durations) / len(durations),
                    'min_duration_ms': min(durations),
                    'max_duration_ms': max(durations),
                    'baseline_ms': self.baseline_metrics.get(op)
                }

        return summary

    def reset_baseline(self, operation_name: Optional[str] = None) -> None:
        """Reset performance baseline."""
        if operation_name:
            self.baseline_metrics.pop(operation_name, None)
            self.logger.info(f"Reset baseline for {operation_name}")
        else:
            self.baseline_metrics.clear()
            self.logger.info("Reset all performance baselines")


# Global performance monitor instance
performance_monitor = PerformanceMonitor()


def track_performance(operation_name: str, **metadata):
    """
    Decorator to track performance of a function.

    Args:
        operation_name: Name of the operation
        **metadata: Additional metadata to store
    """
    def decorator(func):
        def wrapper(*args, **kwargs):
            with performance_monitor.track_operation(operation_name, **metadata):
                return func(*args, **kwargs)
        return wrapper
    return decorator
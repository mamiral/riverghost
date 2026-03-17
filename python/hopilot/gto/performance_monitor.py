"""
Performance monitoring tools for database query execution.

Provides comprehensive monitoring of query performance, execution times,
and database health metrics to ensure optimal system performance.
"""

import asyncio
import time
from typing import Dict, List, Optional, Any, Callable
from datetime import datetime, timedelta
from dataclasses import dataclass
from contextlib import asynccontextmanager
import statistics

from hopilot.database import DatabaseConnection
from hopilot.logging_config import get_logger

logger = get_logger(__name__)


@dataclass
class QueryPerformanceMetrics:
    """Performance metrics for a single query execution."""
    query_name: str
    execution_time: float
    timestamp: datetime
    success: bool
    error_message: Optional[str] = None
    result_count: Optional[int] = None
    metadata: Dict[str, Any] = None


@dataclass
class PerformanceSummary:
    """Summary of performance metrics over a time period."""
    total_queries: int
    successful_queries: int
    failed_queries: int
    average_execution_time: float
    median_execution_time: float
    min_execution_time: float
    max_execution_time: float
    p95_execution_time: float
    p99_execution_time: float
    time_period: timedelta


class QueryPerformanceMonitor:
    """
    Monitor and analyze database query performance.
    """

    def __init__(self, database_url: str):
        self.database_url = database_url
        self.db_connection = DatabaseConnection(database_url)
        self.metrics: List[QueryPerformanceMetrics] = []
        self.max_metrics_history = 10000  # Keep last 10k metrics

    @asynccontextmanager
    async def monitor_query(self, query_name: str, metadata: Optional[Dict[str, Any]] = None):
        """
        Context manager to monitor query execution performance.

        Usage:
            async with monitor.monitor_query("get_strategy_matrix"):
                result = await repo.get_strategy_matrix(...)
        """
        start_time = time.time()
        timestamp = datetime.now()
        success = False
        error_message = None
        result_count = None

        try:
            yield
            success = True
        except Exception as e:
            error_message = str(e)
            raise
        finally:
            execution_time = time.time() - start_time

            metric = QueryPerformanceMetrics(
                query_name=query_name,
                execution_time=execution_time,
                timestamp=timestamp,
                success=success,
                error_message=error_message,
                result_count=result_count,
                metadata=metadata or {}
            )

            self._record_metric(metric)

    def _record_metric(self, metric: QueryPerformanceMetrics):
        """Record a performance metric."""
        self.metrics.append(metric)

        # Maintain history limit
        if len(self.metrics) > self.max_metrics_history:
            self.metrics = self.metrics[-self.max_metrics_history:]

        # Log performance issues
        if metric.execution_time > 5.0:  # Log slow queries > 5 seconds
            logger.warning(
                f"Slow query detected: {metric.query_name} took {metric.execution_time:.2f}s"
            )
        elif not metric.success:
            logger.error(
                f"Failed query: {metric.query_name} - {metric.error_message}"
            )

    async def get_performance_summary(self, hours: int = 1) -> PerformanceSummary:
        """
        Get performance summary for the specified time period.

        Args:
            hours: Number of hours to analyze (default: 1)

        Returns:
            Performance summary statistics
        """
        def _calculate_summary() -> PerformanceSummary:
            cutoff_time = datetime.now() - timedelta(hours=hours)

            # Filter metrics for the time period
            recent_metrics = [
                m for m in self.metrics
                if m.timestamp >= cutoff_time
            ]

            if not recent_metrics:
                return PerformanceSummary(
                    total_queries=0,
                    successful_queries=0,
                    failed_queries=0,
                    average_execution_time=0,
                    median_execution_time=0,
                    min_execution_time=0,
                    max_execution_time=0,
                    p95_execution_time=0,
                    p99_execution_time=0,
                    time_period=timedelta(hours=hours)
                )

            execution_times = [m.execution_time for m in recent_metrics]
            successful_metrics = [m for m in recent_metrics if m.success]

            return PerformanceSummary(
                total_queries=len(recent_metrics),
                successful_queries=len(successful_metrics),
                failed_queries=len(recent_metrics) - len(successful_metrics),
                average_execution_time=statistics.mean(execution_times),
                median_execution_time=statistics.median(execution_times),
                min_execution_time=min(execution_times),
                max_execution_time=max(execution_times),
                p95_execution_time=statistics.quantiles(execution_times, n=20)[18] if len(execution_times) >= 20 else max(execution_times),
                p99_execution_time=statistics.quantiles(execution_times, n=100)[98] if len(execution_times) >= 100 else max(execution_times),
                time_period=timedelta(hours=hours)
            )

        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, _calculate_summary)

    async def get_slow_queries(self, threshold_seconds: float = 1.0,
                              hours: int = 1) -> List[QueryPerformanceMetrics]:
        """
        Get slow queries above the specified threshold.

        Args:
            threshold_seconds: Minimum execution time to be considered slow
            hours: Number of hours to analyze

        Returns:
            List of slow query metrics
        """
        def _get_slow_queries() -> List[QueryPerformanceMetrics]:
            cutoff_time = datetime.now() - timedelta(hours=hours)

            return [
                m for m in self.metrics
                if m.timestamp >= cutoff_time
                and m.execution_time >= threshold_seconds
            ]

        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, _get_slow_queries)

    async def get_failed_queries(self, hours: int = 1) -> List[QueryPerformanceMetrics]:
        """
        Get failed queries for the specified time period.

        Args:
            hours: Number of hours to analyze

        Returns:
            List of failed query metrics
        """
        def _get_failed_queries() -> List[QueryPerformanceMetrics]:
            cutoff_time = datetime.now() - timedelta(hours=hours)

            return [
                m for m in self.metrics
                if m.timestamp >= cutoff_time
                and not m.success
            ]

        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, _get_failed_queries)

    async def get_query_type_performance(self, hours: int = 1) -> Dict[str, PerformanceSummary]:
        """
        Get performance summary grouped by query type.

        Args:
            hours: Number of hours to analyze

        Returns:
            Dictionary mapping query names to their performance summaries
        """
        def _calculate_query_type_performance() -> Dict[str, PerformanceSummary]:
            cutoff_time = datetime.now() - timedelta(hours=hours)

            # Group metrics by query name
            query_groups: Dict[str, List[QueryPerformanceMetrics]] = {}
            for metric in self.metrics:
                if metric.timestamp >= cutoff_time:
                    if metric.query_name not in query_groups:
                        query_groups[metric.query_name] = []
                    query_groups[metric.query_name].append(metric)

            # Calculate summary for each query type
            summaries = {}
            for query_name, metrics in query_groups.items():
                execution_times = [m.execution_time for m in metrics]
                successful_metrics = [m for m in metrics if m.success]

                summaries[query_name] = PerformanceSummary(
                    total_queries=len(metrics),
                    successful_queries=len(successful_metrics),
                    failed_queries=len(metrics) - len(successful_metrics),
                    average_execution_time=statistics.mean(execution_times) if execution_times else 0,
                    median_execution_time=statistics.median(execution_times) if execution_times else 0,
                    min_execution_time=min(execution_times) if execution_times else 0,
                    max_execution_time=max(execution_times) if execution_times else 0,
                    p95_execution_time=statistics.quantiles(execution_times, n=20)[18] if len(execution_times) >= 20 else (max(execution_times) if execution_times else 0),
                    p99_execution_time=statistics.quantiles(execution_times, n=100)[98] if len(execution_times) >= 100 else (max(execution_times) if execution_times else 0),
                    time_period=timedelta(hours=hours)
                )

            return summaries

        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, _calculate_query_type_performance)

    async def get_database_health_metrics(self) -> Dict[str, Any]:
        """
        Get database health and performance metrics.

        Returns:
            Dictionary with database health information
        """
        def _get_health_metrics() -> Dict[str, Any]:
            try:
                with self.db_connection.session() as session:
                    # Get basic table statistics
                    tables = [
                        'Simulations', 'HandMatrices', 'MatrixCells',
                        'AggregatedMetrics', 'GameStates', 'Players',
                        'Bets', 'BoardCards', 'Jackpots'
                    ]

                    table_stats = {}
                    total_rows = 0

                    for table in tables:
                        try:
                            count = session.execute(text(f"SELECT COUNT(*) FROM {table}")).scalar()
                            table_stats[table] = count
                            total_rows += count
                        except Exception as e:
                            table_stats[table] = f"Error: {str(e)}"

                    # Get database file size (SQLite specific)
                    try:
                        db_size = session.execute(text("SELECT page_count * page_size as size FROM pragma_page_count(), pragma_page_size()")).scalar()
                        db_size_mb = db_size / (1024 * 1024) if db_size else 0
                    except:
                        db_size_mb = None

                    # Get connection pool stats if available
                    pool_stats = {}
                    if hasattr(self.db_connection.engine.pool, '_pool'):
                        pool = self.db_connection.engine.pool._pool
                        pool_stats = {
                            'pool_size': getattr(pool, 'size', None),
                            'checked_out': getattr(pool, 'checkedout', None),
                            'overflow': getattr(pool, 'overflow', None)
                        }

                    return {
                        'table_row_counts': table_stats,
                        'total_database_rows': total_rows,
                        'database_size_mb': db_size_mb,
                        'connection_pool': pool_stats,
                        'timestamp': datetime.now().isoformat()
                    }

            except Exception as e:
                logger.error(f"Health metrics collection failed: {e}")
                return {
                    'error': str(e),
                    'timestamp': datetime.now().isoformat()
                }

        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, _get_health_metrics)

    def clear_metrics(self):
        """Clear all stored performance metrics."""
        self.metrics.clear()
        logger.info("Performance metrics cleared")

    def get_metrics_count(self) -> int:
        """Get the number of stored metrics."""
        return len(self.metrics)
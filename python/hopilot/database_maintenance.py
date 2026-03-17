"""
Database health monitoring and maintenance utilities.

This module provides monitoring, alerting, and maintenance capabilities
for the poker analysis database.
"""

import asyncio
import os
import shutil
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
from pathlib import Path

from hopilot.logging_config import get_logger
from hopilot.database import DatabaseConnection

logger = get_logger(__name__)


class DatabaseHealthMonitor:
    """
    Monitors database health and performance metrics.
    """

    def __init__(self, database_url: str):
        self.database_url = database_url
        self.db_connection = DatabaseConnection(database_url)
        self.alerts = []

    async def check_database_health(self) -> Dict[str, Any]:
        """
        Perform comprehensive database health check.

        Returns:
            Health check report
        """
        report = {
            'timestamp': datetime.now().isoformat(),
            'overall_status': 'healthy',
            'checks': {},
            'alerts': []
        }

        # Run individual health checks
        checks = [
            ('connection', self._check_connection),
            ('schema_integrity', self._check_schema_integrity),
            ('data_consistency', self._check_data_consistency),
            ('performance', self._check_performance),
            ('storage', self._check_storage),
        ]

        for check_name, check_func in checks:
            try:
                result = await check_func()
                report['checks'][check_name] = result

                if result['status'] == 'unhealthy':
                    report['overall_status'] = 'unhealthy'
                    report['alerts'].append(f"{check_name}: {result.get('message', 'Unknown issue')}")

            except Exception as e:
                logger.error(f"Health check {check_name} failed: {e}")
                report['checks'][check_name] = {
                    'status': 'error',
                    'message': str(e)
                }
                report['overall_status'] = 'unhealthy'
                report['alerts'].append(f"{check_name} check failed: {str(e)}")

        return report

    async def _check_connection(self) -> Dict[str, Any]:
        """Check database connection health."""
        try:
            with self.db_connection.session_scope() as session:
                session.execute("SELECT 1")
            return {'status': 'healthy', 'message': 'Connection successful'}
        except Exception as e:
            return {'status': 'unhealthy', 'message': f'Connection failed: {str(e)}'}

    async def _check_schema_integrity(self) -> Dict[str, Any]:
        """Check schema integrity."""
        try:
            with self.db_connection.session_scope() as session:
                # Check for required tables
                required_tables = [
                    'Simulations', 'HandMatrices', 'MatrixCells',
                    'AggregatedMetrics', 'ConvergenceTracking'
                ]

                inspector = self.db_connection._engine  # Access to SQLAlchemy inspector
                from sqlalchemy import inspect
                inspector = inspect(self.db_connection._engine)

                existing_tables = inspector.get_table_names()
                missing_tables = [t for t in required_tables if t not in existing_tables]

                if missing_tables:
                    return {
                        'status': 'unhealthy',
                        'message': f'Missing tables: {missing_tables}'
                    }

                return {'status': 'healthy', 'message': 'All required tables present'}

        except Exception as e:
            return {'status': 'unhealthy', 'message': f'Schema check failed: {str(e)}'}

    async def _check_data_consistency(self) -> Dict[str, Any]:
        """Check data consistency."""
        try:
            with self.db_connection.session_scope() as session:
                # Check for orphaned records
                orphaned_count = session.execute("""
                    SELECT COUNT(*) FROM AggregatedMetrics am
                    LEFT JOIN MatrixCells mc ON am.cell_id = mc.id
                    WHERE mc.id IS NULL
                """).scalar()

                if orphaned_count > 0:
                    return {
                        'status': 'unhealthy',
                        'message': f'Found {orphaned_count} orphaned AggregatedMetrics records'
                    }

                return {'status': 'healthy', 'message': 'Data consistency verified'}

        except Exception as e:
            return {'status': 'unhealthy', 'message': f'Data consistency check failed: {str(e)}'}

    async def _check_performance(self) -> Dict[str, Any]:
        """Check database performance metrics."""
        try:
            with self.db_connection.session_scope() as session:
                # Check query performance on a simple query
                import time
                start_time = time.time()
                session.execute("SELECT COUNT(*) FROM Simulations").scalar()
                query_time = (time.time() - start_time) * 1000

                if query_time > 100:  # 100ms threshold for simple queries
                    return {
                        'status': 'unhealthy',
                        'message': f'Slow query performance: {query_time:.1f}ms'
                    }

                return {'status': 'healthy', 'message': f'Query performance: {query_time:.1f}ms'}

        except Exception as e:
            return {'status': 'unhealthy', 'message': f'Performance check failed: {str(e)}'}

    async def _check_storage(self) -> Dict[str, Any]:
        """Check database storage usage."""
        try:
            # For SQLite, check file size
            if self.database_url.startswith('sqlite:///'):
                db_path = self.database_url.replace('sqlite:///', '')
                if os.path.exists(db_path):
                    size_mb = os.path.getsize(db_path) / (1024 * 1024)
                    if size_mb > 1000:  # 1GB threshold
                        return {
                            'status': 'warning',
                            'message': f'Large database size: {size_mb:.1f}MB'
                        }
                    return {'status': 'healthy', 'message': f'Database size: {size_mb:.1f}MB'}
                else:
                    return {'status': 'unhealthy', 'message': 'Database file not found'}

            return {'status': 'healthy', 'message': 'Storage check not applicable'}

        except Exception as e:
            return {'status': 'unhealthy', 'message': f'Storage check failed: {str(e)}'}

    def get_alerts(self) -> List[str]:
        """Get current alerts."""
        return self.alerts.copy()

    def clear_alerts(self):
        """Clear all alerts."""
        self.alerts.clear()


class DatabaseBackupManager:
    """
    Manages database backup and recovery operations.
    """

    def __init__(self, database_url: str, backup_directory: str = "backups"):
        self.database_url = database_url
        self.backup_dir = Path(backup_directory)
        self.backup_dir.mkdir(parents=True, exist_ok=True)

    async def create_backup(self, backup_name: Optional[str] = None) -> Dict[str, Any]:
        """
        Create a database backup.

        Args:
            backup_name: Optional name for the backup file

        Returns:
            Backup operation result
        """
        if backup_name is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_name = f"backup_{timestamp}"

        result = {
            'success': False,
            'backup_path': None,
            'size': 0,
            'timestamp': datetime.now().isoformat()
        }

        try:
            if self.database_url.startswith('sqlite:///'):
                db_path = self.database_url.replace('sqlite:///', '')
                if os.path.exists(db_path):
                    backup_path = self.backup_dir / f"{backup_name}.db"
                    shutil.copy2(db_path, backup_path)

                    result['success'] = True
                    result['backup_path'] = str(backup_path)
                    result['size'] = os.path.getsize(backup_path)

                    logger.info(f"Database backup created: {backup_path}")
                else:
                    result['error'] = "Database file not found"
            else:
                result['error'] = "Backup not supported for this database type"

        except Exception as e:
            result['error'] = str(e)
            logger.error(f"Backup creation failed: {e}")

        return result

    async def list_backups(self) -> List[Dict[str, Any]]:
        """
        List available backups.

        Returns:
            List of backup information
        """
        backups = []

        try:
            for backup_file in self.backup_dir.glob("*.db"):
                stat = backup_file.stat()
                backups.append({
                    'name': backup_file.stem,
                    'path': str(backup_file),
                    'size': stat.st_size,
                    'created': datetime.fromtimestamp(stat.st_ctime).isoformat(),
                    'modified': datetime.fromtimestamp(stat.st_mtime).isoformat()
                })

            # Sort by creation time, newest first
            backups.sort(key=lambda x: x['created'], reverse=True)

        except Exception as e:
            logger.error(f"Failed to list backups: {e}")

        return backups

    async def restore_backup(self, backup_name: str) -> Dict[str, Any]:
        """
        Restore database from backup.

        Args:
            backup_name: Name of the backup to restore

        Returns:
            Restore operation result
        """
        result = {
            'success': False,
            'timestamp': datetime.now().isoformat()
        }

        try:
            backup_path = self.backup_dir / f"{backup_name}.db"
            if not backup_path.exists():
                result['error'] = f"Backup not found: {backup_name}"
                return result

            if self.database_url.startswith('sqlite:///'):
                db_path = self.database_url.replace('sqlite:///', '')

                # Create backup of current database before restore
                if os.path.exists(db_path):
                    pre_restore_backup = self.backup_dir / f"pre_restore_{datetime.now().strftime('%Y%m%d_%H%M%S')}.db"
                    shutil.copy2(db_path, pre_restore_backup)
                    result['pre_restore_backup'] = str(pre_restore_backup)

                # Restore from backup
                shutil.copy2(backup_path, db_path)
                result['success'] = True

                logger.info(f"Database restored from backup: {backup_name}")
            else:
                result['error'] = "Restore not supported for this database type"

        except Exception as e:
            result['error'] = str(e)
            logger.error(f"Backup restore failed: {e}")

        return result

    async def cleanup_old_backups(self, keep_days: int = 30) -> Dict[str, Any]:
        """
        Clean up old backups.

        Args:
            keep_days: Number of days of backups to keep

        Returns:
            Cleanup operation result
        """
        result = {
            'deleted_backups': [],
            'kept_backups': [],
            'timestamp': datetime.now().isoformat()
        }

        try:
            cutoff_date = datetime.now() - timedelta(days=keep_days)

            for backup_file in self.backup_dir.glob("*.db"):
                file_date = datetime.fromtimestamp(backup_file.stat().st_ctime)

                if file_date < cutoff_date:
                    backup_file.unlink()
                    result['deleted_backups'].append(backup_file.name)
                    logger.info(f"Deleted old backup: {backup_file.name}")
                else:
                    result['kept_backups'].append(backup_file.name)

        except Exception as e:
            result['error'] = str(e)
            logger.error(f"Backup cleanup failed: {e}")

        return result


class DatabaseMaintenanceScheduler:
    """
    Schedules automated database maintenance tasks.
    """

    def __init__(self, database_url: str):
        self.database_url = database_url
        self.db_connection = DatabaseConnection(database_url)
        self.maintenance_tasks = []

    async def run_maintenance(self) -> Dict[str, Any]:
        """
        Run scheduled maintenance tasks.

        Returns:
            Maintenance report
        """
        report = {
            'timestamp': datetime.now().isoformat(),
            'tasks_run': [],
            'errors': []
        }

        # Vacuum database (SQLite optimization)
        try:
            with self.db_connection.session_scope() as session:
                session.execute("VACUUM")
            report['tasks_run'].append('vacuum')
            logger.info("Database vacuum completed")
        except Exception as e:
            report['errors'].append(f'Vacuum failed: {str(e)}')

        # Analyze query performance (if supported)
        try:
            with self.db_connection.session_scope() as session:
                session.execute("ANALYZE")
            report['tasks_run'].append('analyze')
            logger.info("Database analyze completed")
        except Exception as e:
            # ANALYZE might not be supported
            pass

        return report

    async def optimize_indexes(self) -> Dict[str, Any]:
        """
        Optimize database indexes.

        Returns:
            Optimization report
        """
        report = {
            'timestamp': datetime.now().isoformat(),
            'indexes_optimized': 0,
            'errors': []
        }

        try:
            with self.db_connection.session_scope() as session:
                # Rebuild indexes (SQLite specific)
                session.execute("REINDEX")
                report['indexes_optimized'] = 1  # Simplified
                logger.info("Database indexes optimized")

        except Exception as e:
            report['errors'].append(str(e))
            logger.error(f"Index optimization failed: {e}")

        return report
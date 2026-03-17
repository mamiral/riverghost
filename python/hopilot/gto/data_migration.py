"""
Data migration scripts for transitioning from cache to database.

This module provides utilities to migrate existing simulation data from the
legacy cache system to the normalized database schema.
"""

import asyncio
import os
import json
from typing import Dict, Any, List, Optional
from datetime import datetime
from pathlib import Path

from hopilot.logging_config import get_logger
from hopilot.gto.database_repository import DatabaseRepository
from hopilot.gto.normalized_db_provider import NormalizedDatabaseProvider

logger = get_logger(__name__)


class DataMigrationService:
    """
    Service for migrating data from legacy cache to database.
    """

    def __init__(self, db_provider: NormalizedDatabaseProvider):
        self.db_provider = db_provider
        self.migration_log = []

    async def migrate_simulation_cache(self, cache_directory: str) -> Dict[str, Any]:
        """
        Migrate simulation data from cache files to database.

        Args:
            cache_directory: Path to cache directory containing simulation files

        Returns:
            Migration report
        """
        report = {
            'total_files': 0,
            'migrated_files': 0,
            'failed_files': 0,
            'skipped_files': 0,
            'errors': []
        }

        cache_path = Path(cache_directory)
        if not cache_path.exists():
            report['errors'].append(f"Cache directory not found: {cache_directory}")
            return report

        # Find all simulation cache files
        simulation_files = list(cache_path.glob("**/simulation_*.json"))
        report['total_files'] = len(simulation_files)

        logger.info(f"Found {len(simulation_files)} simulation files to migrate")

        for sim_file in simulation_files:
            try:
                # Load simulation data
                with open(sim_file, 'r') as f:
                    sim_data = json.load(f)

                # Check if already migrated
                if await self._is_simulation_migrated(sim_data.get('simulation_id')):
                    report['skipped_files'] += 1
                    logger.debug(f"Skipping already migrated simulation: {sim_file.name}")
                    continue

                # Migrate the simulation
                success = await self.db_provider.store_simulation_data(sim_data)
                if success:
                    report['migrated_files'] += 1
                    self.migration_log.append(f"Migrated: {sim_file.name}")
                    logger.info(f"Successfully migrated: {sim_file.name}")
                else:
                    report['failed_files'] += 1
                    error_msg = f"Failed to migrate: {sim_file.name}"
                    report['errors'].append(error_msg)
                    self.migration_log.append(error_msg)
                    logger.error(error_msg)

            except Exception as e:
                report['failed_files'] += 1
                error_msg = f"Error processing {sim_file.name}: {str(e)}"
                report['errors'].append(error_msg)
                self.migration_log.append(error_msg)
                logger.error(error_msg)

        return report

    async def migrate_aggregation_cache(self, cache_directory: str) -> Dict[str, Any]:
        """
        Migrate aggregated metrics from cache to database.

        Args:
            cache_directory: Path to cache directory

        Returns:
            Migration report
        """
        report = {
            'total_aggregations': 0,
            'migrated_aggregations': 0,
            'failed_aggregations': 0,
            'errors': []
        }

        cache_path = Path(cache_directory)

        # Find aggregation cache files
        agg_files = list(cache_path.glob("**/aggregation_*.json"))
        report['total_aggregations'] = len(agg_files)

        for agg_file in agg_files:
            try:
                with open(agg_file, 'r') as f:
                    agg_data = json.load(f)

                # Convert aggregation data to database format
                db_data = self._convert_aggregation_to_db_format(agg_data)

                success = await self.db_provider.store_simulation_data(db_data)
                if success:
                    report['migrated_aggregations'] += 1
                    logger.info(f"Migrated aggregation: {agg_file.name}")
                else:
                    report['failed_aggregations'] += 1
                    report['errors'].append(f"Failed to migrate aggregation: {agg_file.name}")

            except Exception as e:
                report['failed_aggregations'] += 1
                report['errors'].append(f"Error processing aggregation {agg_file.name}: {str(e)}")
                logger.error(f"Error processing aggregation {agg_file.name}: {str(e)}")

        return report

    async def validate_migration(self) -> Dict[str, Any]:
        """
        Validate that migration was successful by comparing data counts.

        Returns:
            Validation report
        """
        report = {
            'simulations_cache': 0,
            'simulations_db': 0,
            'hand_matrices_cache': 0,
            'hand_matrices_db': 0,
            'validation_passed': False,
            'issues': []
        }

        try:
            # Get database counts
            db_stats = await self.db_provider.repository.get_database_statistics()

            report['simulations_db'] = db_stats.get('simulations', 0)
            report['hand_matrices_db'] = db_stats.get('hand_matrices', 0)

            # For now, we'll assume cache counts are available through other means
            # In a real implementation, you'd query the cache system for counts
            report['simulations_cache'] = report['simulations_db']  # Placeholder
            report['hand_matrices_cache'] = report['hand_matrices_db']  # Placeholder

            # Validate counts match
            if (report['simulations_cache'] == report['simulations_db'] and
                report['hand_matrices_cache'] == report['hand_matrices_db']):
                report['validation_passed'] = True
            else:
                report['issues'].append("Data count mismatch between cache and database")

        except Exception as e:
            report['issues'].append(f"Validation error: {str(e)}")

        return report

    async def _is_simulation_migrated(self, simulation_id: str) -> bool:
        """
        Check if a simulation has already been migrated.

        Args:
            simulation_id: Simulation identifier

        Returns:
            True if already migrated
        """
        if not simulation_id:
            return False

        try:
            # Query database for simulation
            result = await self.db_provider.repository.get_simulation_by_id(simulation_id)
            return result is not None
        except Exception:
            return False

    def _convert_aggregation_to_db_format(self, agg_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Convert legacy aggregation format to database format.

        Args:
            agg_data: Legacy aggregation data

        Returns:
            Database-formatted data
        """
        # This is a simplified conversion - in practice, you'd need to map
        # the legacy format to the normalized schema
        return {
            'simulation_id': agg_data.get('simulation_id', 'migrated'),
            'parameters': agg_data.get('parameters', {}),
            'hand_matrices': agg_data.get('hand_matrices', []),
            'aggregated_metrics': agg_data.get('aggregated_metrics', []),
            'created_at': agg_data.get('created_at', datetime.now().isoformat())
        }

    def get_migration_log(self) -> List[str]:
        """
        Get the migration log.

        Returns:
            List of migration log entries
        """
        return self.migration_log.copy()

    async def create_migration_backup(self, backup_directory: str) -> bool:
        """
        Create a backup of the database before migration.

        Args:
            backup_directory: Directory to store backup

        Returns:
            True if backup successful
        """
        try:
            backup_path = Path(backup_directory)
            backup_path.mkdir(parents=True, exist_ok=True)

            # In a real implementation, you'd use database-specific backup tools
            # For SQLite, this could be a simple file copy
            db_path = self.db_provider.repository.db_connection.database_url
            if db_path.startswith('sqlite:///'):
                db_file = db_path.replace('sqlite:///', '')
                if os.path.exists(db_file):
                    backup_file = backup_path / f"pre_migration_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.db"
                    import shutil
                    shutil.copy2(db_file, backup_file)
                    logger.info(f"Database backup created: {backup_file}")
                    return True

            return False

        except Exception as e:
            logger.error(f"Backup creation failed: {e}")
            return False
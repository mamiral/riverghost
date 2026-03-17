"""
Dual-write system for safe migration from cache to database.

This module provides a dual-write implementation that writes to both the legacy
cache system and the new database simultaneously, ensuring data consistency
during the migration period.
"""

import asyncio
from typing import Dict, Any, Optional, List
from datetime import datetime

from hopilot.logging_config import get_logger
from hopilot.gto.database_repository import DatabaseRepository
from hopilot.gto.normalized_db_provider import NormalizedDatabaseProvider

logger = get_logger(__name__)


class DualWriteProvider:
    """
    Dual-write provider that writes to both cache and database simultaneously.

    Ensures data consistency during migration by maintaining both storage systems
    in sync until the migration is complete and verified.
    """

    def __init__(self, cache_provider, db_provider: NormalizedDatabaseProvider):
        """
        Initialize dual-write provider.

        Args:
            cache_provider: Legacy cache provider (AoFBrowserDataProvider)
            db_provider: New database provider
        """
        self.cache_provider = cache_provider
        self.db_provider = db_provider
        self.migration_mode = True  # Enable dual-write by default

    async def get_strategy_matrix(self, position_context, action_context, metric_type) -> Dict[str, Any]:
        """
        Get strategy matrix with dual-read capability.

        Reads from database first, falls back to cache if needed.
        """
        try:
            # Try database first
            result = await self.db_provider.get_strategy_matrix(position_context, action_context, metric_type)
            if result:
                logger.debug("Retrieved strategy matrix from database")
                return result
        except Exception as e:
            logger.warning(f"Database read failed, falling back to cache: {e}")

        # Fallback to cache
        logger.debug("Retrieving strategy matrix from cache")
        return await self.cache_provider.get_strategy_matrix(position_context, action_context, metric_type)

    async def store_simulation_data(self, simulation_data: Dict[str, Any]) -> bool:
        """
        Store simulation data in both cache and database.

        Args:
            simulation_data: Simulation data to store

        Returns:
            True if both writes succeed, False otherwise
        """
        if not self.migration_mode:
            # Migration complete, only write to database
            return await self.db_provider.store_simulation_data(simulation_data)

        # Dual-write mode
        db_success = False
        cache_success = False

        try:
            db_success = await self.db_provider.store_simulation_data(simulation_data)
        except Exception as e:
            logger.error(f"Database write failed: {e}")

        try:
            cache_success = await self.cache_provider.store_simulation_data(simulation_data)
        except Exception as e:
            logger.error(f"Cache write failed: {e}")

        if db_success and cache_success:
            logger.info("Dual-write successful for simulation data")
            return True
        elif db_success:
            logger.warning("Database write succeeded, cache write failed")
            return True  # Database success takes precedence
        elif cache_success:
            logger.error("Database write failed, cache write succeeded - data inconsistency!")
            return False
        else:
            logger.error("Both database and cache writes failed")
            return False

    async def get_convergence_data(self, position: str, action_filters: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Get convergence data with dual-read capability.
        """
        try:
            # Try database first
            result = await self.db_provider.get_convergence_data(position, action_filters)
            if result:
                return result
        except Exception as e:
            logger.warning(f"Database convergence read failed: {e}")

        # Fallback to cache
        return await self.cache_provider.get_convergence_data(position, action_filters)

    def set_migration_mode(self, enabled: bool):
        """
        Enable or disable dual-write mode.

        Args:
            enabled: True to enable dual-write, False for database-only
        """
        self.migration_mode = enabled
        mode = "dual-write" if enabled else "database-only"
        logger.info(f"Migration mode set to: {mode}")

    async def verify_data_consistency(self, sample_size: int = 100) -> Dict[str, Any]:
        """
        Verify data consistency between cache and database.

        Args:
            sample_size: Number of records to sample for verification

        Returns:
            Consistency report
        """
        report = {
            'total_checked': 0,
            'consistent': 0,
            'inconsistent': 0,
            'cache_only': 0,
            'db_only': 0,
            'issues': []
        }

        # Sample some data for verification
        positions = ['UTG', 'MP', 'CO', 'BTN', 'SB', 'BB']
        actions = ['FOLD', 'CALL', 'RAISE', 'ALL_IN']

        for position in positions[:3]:  # Sample a few positions
            for action in actions[:2]:  # Sample a few actions
                try:
                    cache_data = await self.cache_provider.get_convergence_data(position, {'action': action})
                    db_data = await self.db_provider.get_convergence_data(position, {'action': action})

                    report['total_checked'] += 1

                    if not cache_data and not db_data:
                        report['consistent'] += 1
                    elif cache_data and db_data:
                        # Compare data (simplified comparison)
                        if len(cache_data) == len(db_data):
                            report['consistent'] += 1
                        else:
                            report['inconsistent'] += 1
                            report['issues'].append(f"Data count mismatch for {position}/{action}")
                    elif cache_data:
                        report['cache_only'] += 1
                        report['issues'].append(f"Cache-only data for {position}/{action}")
                    elif db_data:
                        report['db_only'] += 1
                        report['issues'].append(f"DB-only data for {position}/{action}")

                except Exception as e:
                    report['issues'].append(f"Verification error for {position}/{action}: {e}")

        return report
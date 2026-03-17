"""
Feature flags for gradual rollout of database integration.

This module provides feature flag management to enable gradual rollout
of database features while maintaining backward compatibility.
"""

import os
from typing import Dict, Any, Optional
from enum import Enum

from hopilot.logging_config import get_logger

logger = get_logger(__name__)


class FeatureFlag(Enum):
    """Enumeration of available feature flags."""

    DATABASE_READS = "database_reads"
    DATABASE_WRITES = "database_writes"
    DUAL_WRITE_MODE = "dual_write_mode"
    CACHE_FALLBACK = "cache_fallback"
    PERFORMANCE_MONITORING = "performance_monitoring"
    SCHEMA_VALIDATION = "schema_validation"
    COMPLEX_QUERIES = "complex_queries"


class FeatureFlagManager:
    """
    Manages feature flags for database integration rollout.

    Provides centralized control over which features are enabled,
    allowing for gradual rollout and rollback capabilities.
    """

    def __init__(self, config_file: Optional[str] = None):
        """
        Initialize feature flag manager.

        Args:
            config_file: Path to feature flag configuration file
        """
        self.config_file = config_file or "config/feature_flags.yaml"
        self.flags: Dict[str, bool] = {}
        self._load_flags()

    def _load_flags(self):
        """Load feature flags from configuration."""
        # Default flags (conservative settings)
        default_flags = {
            FeatureFlag.DATABASE_READS.value: False,
            FeatureFlag.DATABASE_WRITES.value: False,
            FeatureFlag.DUAL_WRITE_MODE.value: True,  # Safe default
            FeatureFlag.CACHE_FALLBACK.value: True,
            FeatureFlag.PERFORMANCE_MONITORING.value: False,
            FeatureFlag.SCHEMA_VALIDATION.value: False,
            FeatureFlag.COMPLEX_QUERIES.value: False,
        }

        # Try to load from environment variables first
        for flag in FeatureFlag:
            env_var = f"HOPILOT_{flag.value.upper()}"
            env_value = os.getenv(env_var)
            if env_value is not None:
                default_flags[flag.value] = env_value.lower() in ('true', '1', 'yes', 'on')

        # Try to load from config file
        try:
            import yaml
            if os.path.exists(self.config_file):
                with open(self.config_file, 'r') as f:
                    file_flags = yaml.safe_load(f) or {}
                    default_flags.update(file_flags)
        except ImportError:
            logger.warning("PyYAML not available, using environment variables only")
        except Exception as e:
            logger.warning(f"Failed to load feature flags from {self.config_file}: {e}")

        self.flags = default_flags
        logger.info(f"Feature flags loaded: {self.flags}")

    def is_enabled(self, flag: FeatureFlag) -> bool:
        """
        Check if a feature flag is enabled.

        Args:
            flag: Feature flag to check

        Returns:
            True if enabled, False otherwise
        """
        return self.flags.get(flag.value, False)

    def enable(self, flag: FeatureFlag):
        """
        Enable a feature flag.

        Args:
            flag: Feature flag to enable
        """
        self.flags[flag.value] = True
        logger.info(f"Feature flag enabled: {flag.value}")
        self._save_flags()

    def disable(self, flag: FeatureFlag):
        """
        Disable a feature flag.

        Args:
            flag: Feature flag to disable
        """
        self.flags[flag.value] = False
        logger.info(f"Feature flag disabled: {flag.value}")
        self._save_flags()

    def set_flag(self, flag: FeatureFlag, enabled: bool):
        """
        Set a feature flag to a specific state.

        Args:
            flag: Feature flag to set
            enabled: True to enable, False to disable
        """
        if enabled:
            self.enable(flag)
        else:
            self.disable(flag)

    def get_all_flags(self) -> Dict[str, bool]:
        """
        Get all feature flags and their current state.

        Returns:
            Dictionary of all flags
        """
        return self.flags.copy()

    def _save_flags(self):
        """Save current flags to configuration file."""
        try:
            import yaml
            os.makedirs(os.path.dirname(self.config_file), exist_ok=True)
            with open(self.config_file, 'w') as f:
                yaml.dump(self.flags, f, default_flow_style=False)
        except ImportError:
            logger.warning("PyYAML not available, flags not persisted to file")
        except Exception as e:
            logger.warning(f"Failed to save feature flags: {e}")

    def get_rollout_status(self) -> Dict[str, Any]:
        """
        Get the current rollout status.

        Returns:
            Dictionary with rollout status information
        """
        status = {
            'phase': 'unknown',
            'description': '',
            'flags': self.get_all_flags()
        }

        # Determine rollout phase based on flag combinations
        if not self.is_enabled(FeatureFlag.DATABASE_READS):
            status['phase'] = 'cache_only'
            status['description'] = 'Using legacy cache system only'
        elif self.is_enabled(FeatureFlag.DUAL_WRITE_MODE):
            status['phase'] = 'dual_write'
            status['description'] = 'Dual-write mode: writing to both cache and database'
        elif self.is_enabled(FeatureFlag.DATABASE_WRITES) and not self.is_enabled(FeatureFlag.CACHE_FALLBACK):
            status['phase'] = 'database_only'
            status['description'] = 'Database-only mode: fully migrated'
        elif self.is_enabled(FeatureFlag.DATABASE_WRITES):
            status['phase'] = 'database_primary'
            status['description'] = 'Database primary with cache fallback'
        else:
            status['phase'] = 'database_reads_only'
            status['description'] = 'Reading from database, writing to cache'

        return status

    def enable_safe_rollout(self):
        """Enable flags for safe initial rollout."""
        self.enable(FeatureFlag.DATABASE_READS)
        self.enable(FeatureFlag.DUAL_WRITE_MODE)
        self.enable(FeatureFlag.CACHE_FALLBACK)
        self.enable(FeatureFlag.PERFORMANCE_MONITORING)
        logger.info("Safe rollout configuration enabled")

    def enable_full_migration(self):
        """Enable flags for full database migration."""
        self.enable(FeatureFlag.DATABASE_READS)
        self.enable(FeatureFlag.DATABASE_WRITES)
        self.disable(FeatureFlag.DUAL_WRITE_MODE)
        self.disable(FeatureFlag.CACHE_FALLBACK)
        self.enable(FeatureFlag.SCHEMA_VALIDATION)
        self.enable(FeatureFlag.COMPLEX_QUERIES)
        logger.info("Full migration configuration enabled")

    def rollback_to_cache(self):
        """Rollback to cache-only mode."""
        self.disable(FeatureFlag.DATABASE_READS)
        self.disable(FeatureFlag.DATABASE_WRITES)
        self.disable(FeatureFlag.DUAL_WRITE_MODE)
        self.enable(FeatureFlag.CACHE_FALLBACK)
        logger.info("Rolled back to cache-only mode")
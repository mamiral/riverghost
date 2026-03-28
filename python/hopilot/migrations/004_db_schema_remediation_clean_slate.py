"""
Database migration script for 004-db-schema-remediation.

This migration implements the "clean slate" approach by dropping existing
MatrixCells and AggregatedMetrics tables to prepare for the GameStates-first
architecture remediation.

Migration ID: 004_db_schema_remediation_clean_slate
Created: 2026-03-21
"""

import os
import sys
from typing import Optional
from datetime import datetime, UTC

# Add the project root to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from hopilot.database import DatabaseConnection
from hopilot.logging_config import get_logger
from sqlalchemy import text

logger = get_logger(__name__)


class Migration004DbSchemaRemediation:
    """
    Migration to prepare for GameStates-first architecture.

    This migration drops existing MatrixCells and AggregatedMetrics tables
    to enable a clean implementation of the corrected data flow.
    """

    MIGRATION_ID = "004_db_schema_remediation_clean_slate"
    DESCRIPTION = "Clean slate migration: Drop MatrixCells and AggregatedMetrics for GameStates-first architecture"

    def __init__(self, database_url: str):
        self.database_url = database_url
        self.connection: Optional[DatabaseConnection] = None

    def is_applied(self) -> bool:
        """
        Check if this migration has already been applied.

        Returns True if MatrixCells and AggregatedMetrics tables don't exist.
        """
        try:
            self.connection = DatabaseConnection(self.database_url)
            with self.connection.session_scope() as session:
                # Check if the old tables still exist
                from sqlalchemy import text
                result = session.execute(text(
                    "SELECT name FROM sqlite_master WHERE type='table' AND name IN ('matrix_cells', 'aggregated_metrics')"
                ))
                existing_tables = [row[0] for row in result]
                return len(existing_tables) == 0
        except Exception as e:
            logger.warning(f"Could not check migration status: {e}")
            return False
        finally:
            if self.connection:
                self.connection.close()

    def apply(self) -> bool:
        """
        Apply the migration by dropping old tables.

        Returns True if successful, False otherwise.
        """
        if self.is_applied():
            logger.info("Migration already applied - old tables don't exist")
            return True

        try:
            self.connection = DatabaseConnection(self.database_url)

            with self.connection._engine.connect() as conn:
                logger.info("Starting clean slate migration...")

                # Drop tables in correct order (respecting foreign keys)
                # Note: SQLite doesn't enforce FK constraints by default, but we drop in safe order anyway

                # Drop AggregatedMetrics first (references MatrixCells)
                try:
                    conn.execute(text("DROP TABLE IF EXISTS aggregated_metrics"))
                    logger.info("Dropped aggregated_metrics table")
                except Exception as e:
                    logger.warning(f"Could not drop aggregated_metrics: {e}")

                # Drop MatrixCells (referenced by GameStates, but we're dropping everything anyway)
                try:
                    conn.execute(text("DROP TABLE IF EXISTS matrix_cells"))
                    logger.info("Dropped matrix_cells table")
                except Exception as e:
                    logger.warning(f"Could not drop matrix_cells: {e}")

                conn.commit()
                logger.info("Migration completed successfully")

                # Record migration in a simple tracking table
                self._record_migration_applied(conn)

                return True

        except Exception as e:
            logger.error(f"Migration failed: {e}")
            return False
        finally:
            if self.connection:
                self.connection.close()

    def rollback(self) -> bool:
        """
        Rollback is not possible for this migration since it drops data.
        This migration is designed to be one-way for the architectural change.

        Returns False to indicate rollback is not supported.
        """
        logger.warning("Rollback not supported for clean slate migration")
        return False

    def _record_migration_applied(self, connection):
        """
        Record that this migration was applied.

        Creates a simple migrations table if it doesn't exist and records this migration.
        """
        try:
            # Create migrations table if it doesn't exist
            connection.execute(text("""
                CREATE TABLE IF NOT EXISTS schema_migrations (
                    id INTEGER PRIMARY KEY,
                    migration_id TEXT UNIQUE NOT NULL,
                    description TEXT,
                    applied_at TEXT NOT NULL
                )
            """))

            # Record this migration
            applied_at = datetime.now(UTC).isoformat()

            connection.execute(text("""
                INSERT OR REPLACE INTO schema_migrations
                (migration_id, description, applied_at)
                VALUES (:migration_id, :description, :applied_at)
            """), {"migration_id": self.MIGRATION_ID, "description": self.DESCRIPTION, "applied_at": applied_at})

            connection.commit()
            logger.info(f"Recorded migration: {self.MIGRATION_ID}")

        except Exception as e:
            logger.warning(f"Could not record migration: {e}")


def run_migration(database_url: str, action: str = "apply") -> bool:
    """
    Run the migration with the specified action.

    Args:
        database_url: SQLAlchemy database URL
        action: "apply" or "rollback"

    Returns:
        True if successful, False otherwise
    """
    migration = Migration004DbSchemaRemediation(database_url)

    if action == "apply":
        logger.info(f"Applying migration: {migration.MIGRATION_ID}")
        return migration.apply()
    elif action == "rollback":
        logger.warning("Attempting rollback (not recommended)")
        return migration.rollback()
    elif action == "status":
        applied = migration.is_applied()
        status = "APPLIED" if applied else "PENDING"
        logger.info(f"Migration {migration.MIGRATION_ID}: {status}")
        return applied
    else:
        logger.error(f"Unknown action: {action}")
        return False


if __name__ == "__main__":
    # Allow running from command line
    import argparse

    parser = argparse.ArgumentParser(description="Database migration for 004-db-schema-remediation")
    parser.add_argument("--database-url", required=True, help="Database URL")
    parser.add_argument("--action", choices=["apply", "rollback", "status"], default="apply", help="Migration action")

    args = parser.parse_args()

    success = run_migration(args.database_url, args.action)
    sys.exit(0 if success else 1)
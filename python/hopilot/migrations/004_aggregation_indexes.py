#!/usr/bin/env python3
"""
Database migration to add indexes for aggregation query optimization.

This migration adds indexes to improve the performance of aggregation queries
by >50% as required by PERF-003.
"""

import logging
from typing import List

from sqlalchemy import text
from hopilot.database import DatabaseConnection

logger = logging.getLogger(__name__)

class AggregationIndexesMigration:
    """Migration to add aggregation optimization indexes."""

    MIGRATION_ID = "004_aggregation_indexes"
    MIGRATION_DESCRIPTION = "Add database indexes to optimize aggregation queries"

    @classmethod
    def apply(cls, database_url: str) -> bool:
        """
        Apply the migration to add aggregation indexes.

        Args:
            database_url: Database connection URL

        Returns:
            True if migration applied successfully
        """
        logger.info(f"Applying migration {cls.MIGRATION_ID}: {cls.MIGRATION_DESCRIPTION}")

        conn = DatabaseConnection(database_url)

        # SQL commands to add indexes
        index_commands = [
            # Composite index for GameState aggregation queries (cell_id + outcome)
            # This optimizes the main aggregation query that filters by cell_id and groups by outcome
            text("""
            CREATE INDEX IF NOT EXISTS ix_game_states_cell_id_outcome
            ON game_states (cell_id, outcome)
            """),

            # Index on GameState round for potential round-based aggregations
            text("""
            CREATE INDEX IF NOT EXISTS ix_game_states_round
            ON game_states (round)
            """),

            # Index on AggregatedMetric convergence_status for status filtering
            text("""
            CREATE INDEX IF NOT EXISTS ix_aggregated_metrics_convergence_status
            ON aggregated_metrics (convergence_status)
            """),

            # Composite index for jackpot queries (game_state_id + jackpot_type)
            # Optimizes jackpot aggregation queries
            text("""
            CREATE INDEX IF NOT EXISTS ix_jackpots_game_state_type
            ON jackpots (game_state_id, jackpot_type)
            """)
        ]

        try:
            with conn.session_scope() as session:
                # Execute each index creation command
                for i, sql in enumerate(index_commands, 1):
                    logger.info(f"Creating index {i}/{len(index_commands)}")
                    session.execute(sql)
                    logger.debug(f"Executed index creation command {i}")

                # Mark migration as applied (skip for test databases without schema_migrations table)
                try:
                    session.execute(
                        text("""
                        INSERT OR REPLACE INTO schema_migrations (migration_id, description, applied_at)
                        VALUES (:migration_id, :description, datetime('now'))
                        """),
                        {
                            'migration_id': cls.MIGRATION_ID,
                            'description': cls.MIGRATION_DESCRIPTION
                        }
                    )
                except Exception as e:
                    logger.warning(f"Could not record migration in schema_migrations table: {e}")
                    logger.info("Continuing without migration tracking (acceptable for test databases)")

                session.commit()
                logger.info(f"Migration {cls.MIGRATION_ID} applied successfully")
                return True

        except Exception as e:
            logger.error(f"Failed to apply migration {cls.MIGRATION_ID}: {e}")
            return False
        finally:
            conn.close()

    @classmethod
    def rollback(cls, database_url: str) -> bool:
        """
        Rollback the migration by dropping the added indexes.

        Args:
            database_url: Database connection URL

        Returns:
            True if rollback successful
        """
        logger.info(f"Rolling back migration {cls.MIGRATION_ID}")

        conn = DatabaseConnection(database_url)

        # SQL commands to drop indexes
        drop_commands = [
            text("DROP INDEX IF EXISTS ix_game_states_cell_id_outcome"),
            text("DROP INDEX IF EXISTS ix_game_states_round"),
            text("DROP INDEX IF EXISTS ix_aggregated_metrics_convergence_status"),
            text("DROP INDEX IF EXISTS ix_jackpots_game_state_type")
        ]

        try:
            with conn.session_scope() as session:
                # Execute each index drop command
                for sql in drop_commands:
                    session.execute(sql)
                    logger.debug(f"Executed: {sql}")

                # Remove migration record (skip if table doesn't exist)
                try:
                    session.execute(
                        text("DELETE FROM schema_migrations WHERE migration_id = :migration_id"),
                        {'migration_id': cls.MIGRATION_ID}
                    )
                except Exception as e:
                    logger.warning(f"Could not remove migration record: {e}")

                session.commit()
                logger.info(f"Migration {cls.MIGRATION_ID} rolled back successfully")
                return True

        except Exception as e:
            logger.error(f"Failed to rollback migration {cls.MIGRATION_ID}: {e}")
            return False
        finally:
            conn.close()

    @classmethod
    def status(cls, database_url: str) -> str:
        """
        Check if migration has been applied.

        Args:
            database_url: Database connection URL

        Returns:
            Migration status string
        """
        conn = DatabaseConnection(database_url)

        try:
            with conn.session_scope() as session:
                result = session.execute(
                    text("SELECT applied_at FROM schema_migrations WHERE migration_id = :migration_id"),
                    {'migration_id': cls.MIGRATION_ID}
                ).fetchone()

                if result:
                    return f"APPLIED (at {result[0]})"
                else:
                    return "PENDING"

        except Exception as e:
            return f"UNKNOWN (schema_migrations table not found: {e})"
        finally:
            conn.close()


def main():
    """Command line interface for the migration."""
    import argparse
    import sys

    parser = argparse.ArgumentParser(description="Aggregation Indexes Migration")
    parser.add_argument("--database-url", default="sqlite:///hopilot.db",
                       help="Database connection URL")
    parser.add_argument("--action", choices=["apply", "rollback", "status"],
                       default="apply", help="Migration action")

    args = parser.parse_args()

    # Configure logging
    logging.basicConfig(level=logging.INFO,
                       format='%(asctime)s - %(levelname)s - %(message)s')

    if args.action == "apply":
        success = AggregationIndexesMigration.apply(args.database_url)
    elif args.action == "rollback":
        success = AggregationIndexesMigration.rollback(args.database_url)
    elif args.action == "status":
        status = AggregationIndexesMigration.status(args.database_url)
        print(f"Migration {AggregationIndexesMigration.MIGRATION_ID}: {status}")
        success = True

    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
"""
Test suite for database migration scripts (TEST-002).

Validates that migration scripts execute correctly and result in valid schema.

PHASE 1: P1 - CRITICAL
- Validates migration script execution
- Ensures schema integrity after migration
- Tests migration idempotency and safety
"""

import os
import tempfile
import pytest
from typing import List
import importlib.util

from hopilot.database import DatabaseConnection
from sqlalchemy import text

# Import the migration module (filename starts with number, so use importlib)
migration_spec = importlib.util.spec_from_file_location(
    'migration_module',
    os.path.join(os.path.dirname(__file__), '..', 'python', 'hopilot', 'migrations', '004_db_schema_remediation_clean_slate.py')
)
migration_module = importlib.util.module_from_spec(migration_spec)
migration_spec.loader.exec_module(migration_module)
Migration004DbSchemaRemediation = migration_module.Migration004DbSchemaRemediation
from hopilot.models import Base


class TestDatabaseMigrations:
    """Test suite for database migration scripts."""

    @pytest.fixture(scope="function")
    def test_db(self):
        """Create a temporary file-based SQLite database for testing."""
        temp_dir = tempfile.mkdtemp()
        db_path = os.path.join(temp_dir, "test.db")
        db_url = f"sqlite:///{db_path}"

        # Create and initialize database with old schema (simulate pre-migration state)
        connection = DatabaseConnection(db_url)

        # Create tables that would exist before migration
        with connection._engine.connect() as conn:
            # Create old tables that the migration should drop
            conn.execute(text("""
                CREATE TABLE IF NOT EXISTS matrix_cells (
                    id INTEGER PRIMARY KEY,
                    matrix_id INTEGER,
                    row_index INTEGER,
                    col_index INTEGER,
                    hand_combination TEXT
                )
            """))

            conn.execute(text("""
                CREATE TABLE IF NOT EXISTS aggregated_metrics (
                    id INTEGER PRIMARY KEY,
                    cell_id INTEGER,
                    equity REAL,
                    last_updated TEXT,
                    FOREIGN KEY (cell_id) REFERENCES matrix_cells(id)
                )
            """))

            # Insert some test data
            conn.execute(text("INSERT INTO matrix_cells (matrix_id, row_index, col_index, hand_combination) VALUES (1, 0, 0, 'AA vs Random')"))
            conn.execute(text("INSERT INTO aggregated_metrics (cell_id, equity, last_updated) VALUES (1, 0.85, '2026-03-22T00:00:00Z')"))

            conn.commit()

        connection.close()

        yield db_url

        # Cleanup - safely remove file
        try:
            import gc
            gc.collect()  # Force garbage collection to release file handles
            if os.path.exists(db_path):
                os.remove(db_path)
            os.rmdir(temp_dir)
        except Exception:
            # Silently ignore cleanup errors on Windows with locked files
            pass

    def test_migration_applies_successfully(self, test_db):
        """Test that the migration applies successfully."""
        migration = Migration004DbSchemaRemediation(test_db)

        # Initially, migration should not be applied (old tables exist)
        assert not migration.is_applied()

        # Apply migration
        result = migration.apply()
        assert result is True

        # After migration, should be applied (old tables gone)
        assert migration.is_applied()

    def test_migration_is_idempotent(self, test_db):
        """Test that running migration multiple times is safe."""
        migration = Migration004DbSchemaRemediation(test_db)

        # Apply migration first time
        result1 = migration.apply()
        assert result1 is True

        # Apply migration second time (should be safe)
        result2 = migration.apply()
        assert result2 is True

        # Should still be applied
        assert migration.is_applied()

    def test_migration_drops_old_tables(self, test_db):
        """Test that migration correctly drops the old tables."""
        migration = Migration004DbSchemaRemediation(test_db)

        # Verify old tables exist before migration
        connection = DatabaseConnection(test_db)
        with connection.session_scope() as session:
            from sqlalchemy import text
            result = session.execute(text(
                "SELECT name FROM sqlite_master WHERE type='table' AND name IN ('matrix_cells', 'aggregated_metrics')"
            ))
            existing_tables = [row[0] for row in result]
            assert 'matrix_cells' in existing_tables
            assert 'aggregated_metrics' in existing_tables

        connection.close()

        # Apply migration
        migration.apply()

        # Verify old tables are gone
        connection = DatabaseConnection(test_db)
        with connection.session_scope() as session:
            result = session.execute(text(
                "SELECT name FROM sqlite_master WHERE type='table' AND name IN ('matrix_cells', 'aggregated_metrics')"
            ))
            existing_tables = [row[0] for row in result]
            assert 'matrix_cells' not in existing_tables
            assert 'aggregated_metrics' not in existing_tables

        connection.close()

    def test_migration_preserves_other_tables(self, test_db):
        """Test that migration doesn't drop unrelated tables."""
        # Create an additional table that should be preserved
        connection = DatabaseConnection(test_db)
        with connection._engine.connect() as conn:
            conn.execute(text("""
                CREATE TABLE test_preserve (
                    id INTEGER PRIMARY KEY,
                    data TEXT
                )
            """))
            conn.execute(text("INSERT INTO test_preserve (data) VALUES ('should remain')"))
            conn.commit()
        connection.close()

        # Apply migration
        migration = Migration004DbSchemaRemediation(test_db)
        migration.apply()

        # Verify the unrelated table still exists
        connection = DatabaseConnection(test_db)
        with connection.session_scope() as session:
            result = session.execute(text(
                "SELECT name FROM sqlite_master WHERE type='table' AND name = 'test_preserve'"
            ))
            existing_tables = [row[0] for row in result]
            assert 'test_preserve' in existing_tables

            # Verify data is still there
            result = session.execute(text("SELECT data FROM test_preserve"))
            data = [row[0] for row in result]
            assert 'should remain' in data

        connection.close()

    def test_migration_rollback_not_supported(self, test_db):
        """Test that migration rollback is not supported."""
        migration = Migration004DbSchemaRemediation(test_db)

        # Apply migration first
        migration.apply()

        # Rollback should return False (not supported)
        rollback_result = migration.rollback()
        assert rollback_result is False

    def test_schema_validation_after_migration(self, test_db):
        """Test that new schema can be created after migration."""
        migration = Migration004DbSchemaRemediation(test_db)
        migration.apply()

        # Now create the new schema
        connection = DatabaseConnection(test_db)
        connection.create_tables()
        connection.close()

        # Verify new tables exist
        connection = DatabaseConnection(test_db)
        with connection.session_scope() as session:
            from sqlalchemy import text
            result = session.execute(text(
                "SELECT name FROM sqlite_master WHERE type='table' AND name IN ('game_states', 'players', 'bets', 'jackpots')"
            ))
            existing_tables = [row[0] for row in result]

            expected_tables = {'game_states', 'players', 'bets', 'jackpots'}
            assert expected_tables.issubset(set(existing_tables))

        connection.close()

    def test_migration_tracking_table_created(self, test_db):
        """Test that migration creates a tracking table."""
        migration = Migration004DbSchemaRemediation(test_db)
        migration.apply()

        # Check if migration tracking table exists
        connection = DatabaseConnection(test_db)
        with connection.session_scope() as session:
            from sqlalchemy import text
            result = session.execute(text(
                "SELECT name FROM sqlite_master WHERE type='table' AND name = 'schema_migrations'"
            ))
            existing_tables = [row[0] for row in result]
            assert 'schema_migrations' in existing_tables

            # Check if our migration is recorded
            result = session.execute(text(
                "SELECT migration_id FROM schema_migrations WHERE migration_id = :migration_id"
            ), {"migration_id": migration.MIGRATION_ID})
            recorded_migrations = [row[0] for row in result]
            assert migration.MIGRATION_ID in recorded_migrations

        connection.close()